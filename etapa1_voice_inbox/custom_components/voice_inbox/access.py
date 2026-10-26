"""No HA dependency: explicit LAN policy and bounded failed-key limiter."""
from collections import OrderedDict, deque
from ipaddress import ip_address, ip_network
import time

def direct_lan(remote, peer, subnet, cloud, forwarded):
    if cloud or forwarded or not remote or not peer:
        return False
    try:
        address = ip_address(remote)
        network = ip_network(subnet, strict=True)
        return address == ip_address(peer) and address in network
    except ValueError:
        return False

def valid_network(value):
    try:
        net = ip_network(value, strict=True)
        allowed = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
        return any(net.version == ip_network(n).version and net.subnet_of(ip_network(n)) for n in allowed)
    except ValueError:
        return False

class Attempts:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.by_ip = OrderedDict()
        self.global_failures = deque(maxlen=50)

    def blocked(self, ip):
        now = self.clock()
        while self.global_failures and self.global_failures[0] <= now - 60:
            self.global_failures.popleft()
        failures = self.by_ip.get(ip, ())
        return len(self.global_failures) >= 50 or sum(t > now - 60 for t in failures) >= 5

    def failure(self, ip):
        now = self.clock()
        if ip not in self.by_ip:
            if len(self.by_ip) >= 256:
                self.by_ip.popitem(last=False)
            self.by_ip[ip] = deque(maxlen=5)
        self.by_ip.move_to_end(ip)
        self.by_ip[ip].append(now)
        self.global_failures.append(now)
