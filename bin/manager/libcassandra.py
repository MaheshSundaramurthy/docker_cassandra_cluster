import re
import os

DEFAULT_CONFIG_LOCATION = '/etc/cassandra/cassandra.yaml'


class CassandraService(object):
    """Simple class to handle cassandra and needs during update"""

    def __init__(self, clustername='MainCluster'):
        super(CassandraService, self).__init__()
        self.seeds = []
        self.clustername = clustername


    def set_seeds(self, seed_list):
        if isinstance(seed_list, list):
            self.seeds += seed_list
        else:
            self.seeds = [seed_list]

    def update_config(self,myip=None):
        orig_config_text = open(DEFAULT_CONFIG_LOCATION, 'r').read()
        # config = yaml.load(stream)
        if None not in self.seeds:
            print("I am not the seed")
            print(self.seeds)
            orig_config_text = re.sub('seeds: "([\d|\.]*)"','seeds: "{}"'.format("".join(self.seeds)),orig_config_text)
            orig_config_text += "auto_bootstrap: false\n"
        #     config['seed_provider'][0]['parameters'][0]['seeds'] = 'REPLACEME'
        orig_config_text = re.sub("cluster_name: '(.*)'","cluster_name: '{}'".format(self.clustername),orig_config_text)
        orig_config_text = re.sub("endpoint_snitch: SimpleSnitch","endpoint_snitch: 'GossipingPropertyFileSnitch'",orig_config_text)
        orig_config_text = re.sub("start_rpc: false","start_rpc: true",orig_config_text)
        if myip is not None:
            orig_config_text = re.sub("listen_address: (.*)","listen_address: {}".format(myip),orig_config_text)
        # config['cluster_name'] = self.clustername
        # config['endpoint_snitch'] = 'GossipingPropertyFileSnitch'
        # config['start_rpc'] = True
        with open(DEFAULT_CONFIG_LOCATION, 'wb+') as newconfig:
            newconfig.write(orig_config_text)
            # ystring = yaml.dump(config).replace('REPLACEME','"{}"'.format(",".join(self.seeds)))
            # print ystring 
            # newconfig.write(ystring)

    def getNodeStatus(self,ip):
        list = []
        result = 1
        p = os.popen("nodetool status")
        while 1:
            line = p.readline()
            # print "Line", line
            if not line =="":
                ipData = line.split(" ")
                if len(ipData) > 3:
                    if ipData[2] == ip:
                        if ipData[0] == "UN":
                                return "OK"
            if not line: break
        return None
