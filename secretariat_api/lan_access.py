"""LAN candidates for tablet pairing, avoiding loopback and VPN defaults."""
import ipaddress
import socket


def lan_addresses():
    rows = []
    try:
        import psutil
        stats = psutil.net_if_stats()
        for name, addresses in psutil.net_if_addrs().items():
            if name in stats and not stats[name].isup:
                continue
            lower = name.lower()
            virtual = lower.startswith(('lo', 'utun', 'tun', 'tap', 'docker', 'veth', 'bridge', 'vmnet', 'awdl', 'llw')) or 'vpn' in lower
            for address in addresses:
                if address.family != socket.AF_INET:
                    continue
                value = ipaddress.ip_address(address.address)
                if value.is_loopback or value.is_unspecified or value.is_link_local:
                    continue
                priority = (virtual, not value.is_private, lower not in ('en0', 'wi-fi', 'wifi', 'wlan0'))
                rows.append((priority, {'address': str(value), 'interface': name}))
    except (ImportError, OSError):
        pass
    if not rows:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(('8.8.8.8', 80))
                address = sock.getsockname()[0]
            if not ipaddress.ip_address(address).is_loopback:
                rows.append(((False, False, False), {'address': address, 'interface': 'LAN'}))
        except OSError:
            pass
    rows.sort(key=lambda row: row[0])
    unique = {}
    for _, item in rows:
        unique.setdefault(item['address'], item)
    return list(unique.values())


def listener_reachable(address, port):
    try:
        with socket.create_connection((address, int(port)), timeout=1):
            return True
    except OSError:
        return False
