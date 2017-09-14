#!/bin/env python

import re
from enum import Enum

class LifeCycleTransition(Enum):
    start = 'autoscaling:EC2_INSTANCE_LAUNCHING'
    term = 'autoscaling:EC2_INSTANCE_TERMINATING'

    @classmethod
    def get_transition(cls_obj, str):
        return getattr(cls_obj, str, None).value

class AvailabilityZones(Enum):
    us_east_1 = ['us-east-1c', 'us-east-1d','us-east-1e']
    us_east_2 = ['us-east-2a', 'us-east-2b','us-east-2c']
    us_west_2 = ['us-west-2a', 'us-west-2b','us-west-2c']

    @classmethod
    def get_region(cls_obj, str):
        region = re.sub('-', '_', str)
        return getattr(cls_obj, region, None).value


def target_lambda_arn(region, target):
    return 'arn:aws:events:%s:628478040924:rule/%s' % (region, target)
