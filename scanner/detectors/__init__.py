"""
Graveyard Shift detectors package.

ALL_DETECTORS is an ordered list of detect functions.
Each has the signature: detect(snapshot: Snapshot, config: dict) -> list[Tombstone]
"""

from scanner.detectors.ebs_snapshots import detect as detect_ebs_snapshots
from scanner.detectors.ebs_volumes import detect as detect_ebs_volumes
from scanner.detectors.ec2_stopped import detect as detect_ec2_stopped
from scanner.detectors.elastic_ips import detect as detect_elastic_ips
from scanner.detectors.iam_keys import detect as detect_iam_keys
from scanner.detectors.load_balancers import detect as detect_load_balancers
from scanner.detectors.log_groups import detect as detect_log_groups
from scanner.detectors.nat_gateways import detect as detect_nat_gateways
from scanner.detectors.security_groups import detect as detect_security_groups

ALL_DETECTORS = [
    detect_ebs_volumes,
    detect_ebs_snapshots,
    detect_elastic_ips,
    detect_load_balancers,
    detect_nat_gateways,
    detect_ec2_stopped,
    detect_iam_keys,
    detect_security_groups,
    detect_log_groups,
]
