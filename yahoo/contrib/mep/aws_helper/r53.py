#!/bin/env/python

import base

class DnsTools(base.Utils):

    # init parent class with region
    def __init__(self, region):
        base.Utils.__init__(self, region)

    def change_status(self, change_id):
        return self.r53_client.get_change(Id = change_id)

    def get_record(self, record_name, record_type):
        return self.r53_client.list_resource_record_sets(
            HostedZoneId = self.r53_zoneid,
            StartRecordName = record_name,
            StartRecordType = record_type
        )

    def get_region_record(self, record_name, record_type, region):
        regions = {}
        get_record = self.get_record(record_name, record_type)
        if 'ResourceRecordSets' in get_record:
            for i in get_record['ResourceRecordSets']:
                if region in i['SetIdentifier']:
                    set_id  = i['SetIdentifier']
                    weight  = i['Weight']
                    ttl     = i['TTL']

                    regions[set_id] = {}
                    regions[set_id]['weight'] = weight
                    regions[set_id]['ttl'] = ttl

                    for a in i['ResourceRecords']:
                        regions[set_id]['cname'] = a['Value']
        return regions

    def change_weight(self, record_name, record_cname, record_type, identifier, weight, ttl, comment, action, region):
        pprint(self)
        return self.r53_client.change_resource_record_sets(
            HostedZoneId = self.r53_zoneid,
            ChangeBatch = {
                'Comment': comment,
                'Changes': [
                    {
                        'Action': action,
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': record_type,
                            'SetIdentifier': identifier,
                            'Weight': weight,
                            'TTL': ttl,
                            'ResourceRecords': [
                                {
                                    'Value': record_cname
                                }
                            ]
                        }
                    }
                ]
            }
        )
