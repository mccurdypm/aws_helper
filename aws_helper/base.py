#!/bin/env python

import re
import sys
import boto3
import time
from configparser import ConfigParser
from botocore.client import Config
from yahoo.contrib.mep.aws_helper.constants import *

class Utils:
    # So the libs will be avail
    # when instantiating new object
    import botocore
    import sys

    def __init__(self, region):
        aws = {}
        if  'accessKeyId' in auth and len(auth) == 5:
            aws = {
                'region_name' : auth['region'],
                'aws_access_key_id' : auth['accessKeyId'],
                'aws_secret_access_key' : auth['secretAccessKey'],
                'aws_session_token' : auth['sessionToken']
            }
        elif 'region' in auth and len(auth) == 1:
            aws['region_name'] = auth['region']
        else:
            sys.exit('No region defined')

        self.logs = boto3.client('logs',  **aws)
        self.ssm = boto3.client('ssm', **aws)
        self.alarm = boto3.client('cloudwatch', **aws)
        self.client = boto3.client('ec2', **aws)
        self.resource = boto3.resource('ec2', **aws)
        self.s3resource = boto3.resource('s3', **aws)
        self.s3client = boto3.client('s3', **aws)
        self.r53_client = boto3.client('route53', **aws)
        self.as_client = boto3.client('autoscaling', **aws)

        # Route53 Zone ID
        self.r53_zoneid = ''

        # IAM profile needs to be associated with all ec2 instances
        # this enables instances the ability to query for tags without auth
        # as well as being able to run shell cmds via aws cli / boto3 sdk
        self.iam_arn = ''

        # sns arn for sending alerts created for each ec2 instance
        # security groups are region specific
        if auth['region'] == 'us-west-2':
            self.dsg_workers = ''
            self.dsg_rmqapi = ''
            self.sns_alarm = '';
        elif auth[region'] == 'us-east-2':
            self.dsg_workers = ''
            self.dsg_rmqapi = ''
            self.sns_alarm = ''
        elif auth['region'] == 'us-east-1':
            self.dsg_workers = ''
            self.dsg_rmqapi = ''
            self.sns_alarm = ''
            
            
    # build tag filter for create/query
    # keyword args:
    #    -multi=1   = only returns a dict, for multiple queries.
    #                 append each result to filter list
    #    -create=1  = for creating tags
    #    -(nothing) = for resource tag query
    def build_filter(self, key, value, **kw):
        if 'create' in kw and kw['create'] == 1:
            filter = [
                {
                    'Key': key,
                    'Value': value
                }
            ]
        elif 'multi' in kw and kw['multi'] == 1:
            filter = {
                'Name': key,
                'Values': [value]
            }
        else:
            filter = [
                {
                    'Name': key,
                    'Values': [value]
                }
            ]

        return filter


    # get latest AMI based on creation date
    def get_latest_ami(self, values):
        timestamp = int(time.time())
        filters = [ { 'Name' : 'name', 'Values': [values] } ]

        try:
            response = self.client.describe_images(Filters = filters)
        except self.botocore.exceptions.ClientError as e:
            print(e)

        amis = sorted(response['Images'], key=lambda sort: sort['CreationDate'])
        if len(amis) > 0:
            return amis[-1]['ImageId']

    def parse_s3_ini(self, env, region, s3_bucket, s3_key, component, options):
        ini_file = '/tmp/%s' % s3_key

        self.s3resource.meta.client.download_file(s3_bucket, s3_key, ini_file)
        component = component.upper()
        parser = ConfigParser()
        parser.read(ini_file)

        if component in parser.sections():
            for option in options:
                parser.set(component, option, options[option])
                with open(ini_file, 'wb') as config:
                    parser.write(config)

        elif component not in parser.sections():
            parser.add_section(component)
            for option in options:
                parser.set(component, option, options[option])
                with open(ini_file, 'wb') as config:
                    parser.write(config)

        self.s3resource.meta.client.upload_file(ini_file, s3_bucket, s3_key)
        os.remove(ini_file)
                  
    def update_ip_r53healthcheck(self, hl_id, ip_address):
        return  self.r53_client.update_health_check(
            HealthCheckId = hl_id,
            IPAddress = ip_address
        )

    def create_elb(self, region, name, proto, elb_port, instance_port):
        return self.elb_client.create_load_balancer(
            LoadBalancerName = name,
            Listeners = [
                {
                    'Protocol': proto,
                    'LoadBalancerPort': elb_port,
                    'InstanceProtocol': proto,
                    'InstancePort': instance_port
                }
            ],
            AvailabilityZones = AvailabilityZones.get_region(region),
            SecurityGroups=[
                self.dsg_api
            ]
        )

    def configure_elb_healthcheck(self, elb_name, target, interval, timeout, u_th, h_th):
        return self.elb_client.configure_health_check(
            LoadBalancerName = elb_name,
            HealthCheck = {
                'Target': target,
                'Interval': interval,
                'Timeout': timeout,
                'UnhealthyThreshold': u_th,
                'HealthyThreshold': h_th
            }
        )

    def get_elb_instances(self, elb_name):
        return self.elb_client.describe_instance_health(LoadBalancerName = elb_name)

    def add_instance_elb(self, elb_name, instances):
        return self.elb_client.register_instances_with_load_balancer(
            LoadBalancerName = elb_name,
            Instances = instances
        )
                  
    def remove_instance_elb(self, elb_name, instances):
        return self.elb_client.deregister_instances_from_load_balancer(
            LoadBalancerName = elb_name,
            Instances = instances
        )
                  
    # json formatting
    def json_pretty(self, json_obj):
        print json.dumps(json_obj, sort_keys=True, indent=4, separators=(',', ': '))

    # query cloudwatch for log streams
    def cloudwatch_logstreams(self, log_group):
        return self.logs.describe_log_streams(logGroupName = log_group)

    # get log events from stream
    def get_log_events(self, log_group, log_stream):
        return self.logs.get_log_events(logGroupName = log_group, logStreamName = log_stream)

    # terminates ec2 instance
    def terminate_ec2(self, instance_ids):
        return self.client.terminate_instances(InstanceIds = instance_ids )

    # stops ec2 instance
    def stop_ec2(self, instance_ids):
        return self.client.stop_instances(InstanceIds = instance_ids)

    # query via tags
    def get_by_tags(self, filter):
        return self.client.describe_tags(Filters=filter)

    # get instance details
    def query_instance(self, instance_ids):
        return self.client.describe_instances(InstanceIds = instance_ids)

    # get instance status
    def instance_status(self, instance_ids):
        return self.client.describe_instance_status(InstanceIds = instance_ids)

    # create tags
    def create_tags(self, instance_ids, filter):
        return self.client.create_tags(Resources = instance_ids, Tags = filter)

    # tag ami ID
    def create_tags_image(self, image_id, filter):
        return self.resource.Image(image_id).create_tags(Tags = filter)

    # remove tags
    def delete_tags(self, resource_ids, filter):
        return self.client.delete_tags(Resources = resource_ids, Tags = filter)

    # reboot ec2 instance
    def reboot_instance(self, instance_ids):
        return self.client.reboot_instances(InstanceIds = instance_ids)
