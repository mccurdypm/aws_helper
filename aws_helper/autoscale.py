#!/bin/env/python

import sys
import time
import base
from constants import *
from pprint import pprint

class Tools(base.Utils):

    # init parent class with region
    def __init__(self, region):
        base.Utils.__init__(self, region)

    def create_lc(self, component, name, instance_type, region):

        if component == 'worker':
            sgroups = [self.dsg_workers]
            ami_id_regex = 'yxs2-1*'
        elif component == 'rmq':
            sgroups = [self.dsg_rmqapi]
            ami_id_regex = 'yxs2-rmq*'

        # get AMI ID
        try:
            ami_id = self.get_latest_ami(ami_id_regex)
        except self.botocore.exceptions.ClientError as e:
            print e

        return self.as_client.create_launch_configuration(
            LaunchConfigurationName = name,
            ImageId = ami_id,
            SecurityGroups = sgroups,
            InstanceType = instance_type,
            UserData = "!/bin/bash\n" \
                    "set -e\n" \
                    "sudo yum update -y\n" \
                    "# Disable requiretty\n" \
                    "sed -r -e 's/^(Defaults\s+requiretty)$/# \1/' -i /etc/sudoers\n" \
                    "# install SSM Agent\n" \
                    "cd /tmp\n" \
                    "curl https://amazon-ssm-%s.s3.amazonaws.com/latest/linux_amd64/amazon-ssm-agent.rpm -o amazon-ssm-agent.rpm\n" \
                    "sudo yum install -y amazon-ssm-agent.rpm\n" % region,

            BlockDeviceMappings = [
                {
                    'DeviceName': '/dev/xvda',
                    'Ebs': {
                        'VolumeSize': 10,
                        'VolumeType': 'gp2'
                    },
                },
            ],
            InstanceMonitoring = {
                'Enabled': True
            },
            IamInstanceProfile = self.iam_arn,
            EbsOptimized = False
        )


    def build_asg_tags(self, asg_name, key, value):
        return {
                    'ResourceId': asg_name,
                    'ResourceType': 'auto-scaling-group',
                    'Key': key,
                    'Value': value,
                    'PropagateAtLaunch': True
                }


    def create_asg(self, component, asg_name, lc_name, min_size, max_size, env, region):

        s3_bucket = 'yxs2-%s-settings' % region
        s3_key = ''

        asg_tags = []
        asg_tags.append(self.build_asg_tags(asg_name, 'env', 'stg_asg'))
        asg_tags.append(self.build_asg_tags(asg_name, 'Name', asg_name))

        if component == 'worker':
            rmq_master_ip = self.s3resource.Object(s3_bucket, s3_key).get()['Body'].read()
            asg_tags.append(self.build_asg_tags(asg_name, 'rmq', rmq_master_ip))
        elif component == 'rmq':
            asg_tags.append(self.build_asg_tags(asg_name, 'cluster', '0'))

        asg = self.as_client.create_auto_scaling_group(
            AutoScalingGroupName = asg_name,
            LaunchConfigurationName = lc_name,
            MinSize = min_size,
            MaxSize = max_size,
            DesiredCapacity = min_size,
            HealthCheckType = 'EC2',
            HealthCheckGracePeriod = 60,
            NewInstancesProtectedFromScaleIn = False,
            AvailabilityZones = AvailabilityZones.get_region(region),
            Tags = asg_tags
        )

        if component == 'rmq':
            print 'RMQ Instances booting up.....'
            time.sleep(30)

            query = self.get_asg(asg_name)
            if query['AutoScalingGroups']:
                instances = query['AutoScalingGroups'][0]['Instances']
                rmq_master = self.query_instance([instances[0]['InstanceId']])
                rmq_master_ip = rmq_master['Reservations'][0]['Instances'][0]['PrivateIpAddress']

                print "Saving Master RMQ IP: %s" % rmq_master_ip
                s3_put = self.s3resource.Object(s3_bucket, s3_key).put(Body = rmq_master_ip)
                print "Success" if s3_put['ResponseMetadata']['HTTPStatusCode'] == 200 else sys.exit("Failed")

                instance_ids = []
                for i in instances:
                    instance_ids.append(i['InstanceId'])

                self.create_tags(instance_ids, self.build_filter('rmq', rmq_master_ip, create=1))

        return asg

    def update_asg(self, asg_name, lc_name, min_size, max_size):
        return self.as_client.update_auto_scaling_group(
            AutoScalingGroupName = asg_name,
            LaunchConfigurationName = lc_name,
            MinSize = min_size,
            MaxSize = max_size,
            NewInstancesProtectedFromScaleIn = False
        )

    def get_asg(self, asg_name):
        return self.as_client.describe_auto_scaling_groups(AutoScalingGroupNames = [asg_name])

    def create_lifecycle_hook(self, hook_name, asg_name, transition, region, target_arn):
        return self.as_client.put_lifecycle_hook(
            LifecycleHookName = hook_name,
            AutoScalingGroupName = asg_name,
            LifecycleTransition = LifeCycleTransition.get_transition(transition)
        )

    # this will be a lambda function
    def complete_lifecycle_hook(self, hook_name, asg_name, token, action_result, instance_id):
        return self.as_client.complete_lifecycle_action(
            LifecycleHookName = hook_name,
            AutoScalingGroupName = asg_name,
            LifecycleActionToken = token,
            LifecycleActionResult = action_result,
            InstanceId = instance_id
        )
