#!/bin/env python

import re
import sys
import time
import base
import dateutil.parser as dp

class Tools(base.Utils):

    # init parent class with region
    def __init__(self, region):
        base.Utils.__init__(self, region)

    # boot ec2 instance
    def boot_ec2(self, count, ami_id, instance_type, component):

        if component == 'worker':
            sgroups = [self.dsg_workers]
        elif component == 'rmq':
            sgroups = [self.dsg_rmqapi]

        response = self.client.run_instances(
            ImageId = ami_id,
            MinCount = 1,
            MaxCount = int(count),
            SecurityGroupIds = sgroups,
            InstanceType = instance_type,
            BlockDeviceMappings = [
                {
                    'DeviceName': '/dev/xvda',
                    'Ebs': {
                        'VolumeSize': 10,
                        'VolumeType': 'gp2'
                    },
                },
            ],
            Monitoring = {
                'Enabled': True
            },
            IamInstanceProfile = {
                'Arn': self.iam_arn,
            },
        )
        return response

    # create cloudwatch alarms
    def create_alarm(self, alarm_name, alarm_desc, metric_name, threshold, instance_id):
        th = float(threshold)
        response = self.alarm.put_metric_alarm(
            AlarmName = alarm_name,
            AlarmDescription = alarm_desc,
            ActionsEnabled = True,
            AlarmActions = [
                self.sns_alarm,
            ],
            MetricName = metric_name,
            Namespace = 'AWS/EC2',
            Statistic = 'Maximum',
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': instance_id
                },
            ],
            Period = 60,
            EvaluationPeriods = 2,
            Threshold = th,
            ComparisonOperator = 'GreaterThanOrEqualToThreshold'
        )
        return response

    # get latest AMI based on creation date
    def get_latest_ami(self, values):
        timestamp = int(time.time())
        filters = [ { 'Name' : 'name', 'Values': [values] } ]

        try:
            response = self.client.describe_images(Filters = filters)
        except self.botocore.exceptions.ClientError as e:
            print e

        amis = {}
        for i in response['Images']:
            creation = i['CreationDate']
            ami_id = i['ImageId']
            tdelta = timestamp - int(dp.parse(creation).strftime('%s'))
            amis[ami_id] = tdelta

        return min(amis, key=amis.get)

    # ec2 launch config
    def ec2_provision(self, region, component, host_count, host_type, host_name):
        ami_id_regex = 'yxs2-1*' if component == 'worker' else 'yxs2-rmq*'
        s3_bucket = 'yxs2-%s-settings' % region
        s3_key = 'rmq_master'

        # get AMI ID
        try:
            ami_id = self.get_latest_ami(ami_id_regex)
        except self.botocore.exceptions.ClientError as e:
            print e

        # launch ec2
        try:
            launch = self.boot_ec2(host_count, ami_id, host_type, component)
        except self.botocore.exceptions.ClientError as e:
            print e

        print "Launching instance(s) ..... "
        time.sleep(5)
        # loop to numerically name ec2 instances
        # production_celery01, 02, 03, etc
        # +1 so range value is consistent with count value
        instance_ids = []
        for i in xrange(1, int(host_count) + 1):
            num = "%.2d" % i
            name_value = "%s%s" % (host_name, num)

            # -1 to iterate though response obj to get instance id
            i = i - 1
            instance_id = launch['Instances'][i]['InstanceId']
            instance_ids.append(instance_id)

            print "Instance: %s" % instance_id
            # instance_id arg needs to be a list
            try:
                self.create_tags([instance_id], self.build_filter('Name', name_value, create=1))
            except self.botocore.exceptions.ClientError as e:
                print e

        # RMQ Master ip S3
        if component == 'rmq':
            rmq_master = self.query_instance([instance_ids[0]])
            rmq_master_ip = rmq_master['Reservations'][0]['Instances'][0]['PrivateIpAddress']
            print "Saving Master RMQ IP: %s" % rmq_master_ip

            s3_put = self.s3resource.Object(s3_bucket, s3_key).put(Body = rmq_master_ip)
            print "Success" if s3_put['ResponseMetadata']['HTTPStatusCode'] == 200 else sys.exit("Failed")

            # set tag cluster to 0 for post deploy clustering
            self.create_tags(instance_ids, self.build_filter('cluster', '0', create=1))
        else:
            print "Getting Master RMQ IP from S3"
            rmq_master_ip = self.s3resource.Object(s3_bucket, s3_key).get()['Body'].read()
            print "RMQ Master IP: %s" % rmq_master_ip

        # tag environment, active rmq and AMI ID
        try:
            self.create_tags(instance_ids, self.build_filter('env', 'stg', create=1))
            self.create_tags(instance_ids, self.build_filter('rmq', rmq_master_ip, create=1))
            self.create_tags(instance_ids, self.build_filter('ami_id', ami_id, create=1))
        except self.botocore.exceptions.ClientError as e:
            print e

        print "Provisioned Instance: %s (id: %s)" % (name_value, instance_id)
