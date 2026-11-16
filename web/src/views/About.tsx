import { CopyButton } from "../components/CopyButton";

const IAM_POLICY = JSON.stringify(
  {
    Version: "2012-10-17",
    Statement: [
      {
        Sid: "GraveyardShiftReadOnly",
        Effect: "Allow",
        Action: [
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots",
          "ec2:DescribeAddresses",
          "ec2:DescribeInstances",
          "ec2:DescribeNatGateways",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeRegions",
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeTargetHealth",
          "cloudwatch:GetMetricStatistics",
          "logs:DescribeLogGroups",
          "logs:DescribeMetricFilters",
          "logs:FilterLogEvents",
          "iam:ListUsers",
          "iam:ListAccessKeys",
          "iam:GetAccessKeyLastUsed",
        ],
        Resource: "*",
      },
    ],
  },
  null,
  2
);

const THRESHOLDS = [
  { key: "ebs_volume_grace_period_hours", default: "24", description: "Skip volumes created within this many hours (provisioning grace)" },
  { key: "ec2_stopped_days",              default: "30", description: "Flag instances stopped for at least this many days" },
  { key: "iam_key_unused_days",           default: "90", description: "Flag access keys unused for this many days" },
  { key: "lb_no_traffic_days",            default: "14", description: "Flag load balancers with zero traffic for this many days" },
  { key: "nat_no_traffic_days",           default: "14", description: "Flag NAT Gateways with ~zero traffic for this many days" },
  { key: "nat_min_bytes",                 default: "1048576 (1 MB)", description: "Minimum bytes threshold for NAT Gateway traffic" },
  { key: "log_group_quiet_days",          default: "30", description: "Flag log groups with no ingestion for this many days" },
];

export function About() {
  return (
    <div className="about">
      <h2 className="view-title">About Graveyard Shift</h2>

      <section className="about-section">
        <h3>What it does</h3>
        <p>
          Graveyard Shift scans an AWS account for zombie resources — things that are
          orphaned, idle, or forgotten — and shows them as tombstones in a haunted graveyard.
          Each tombstone carries a cause of death, an estimated monthly cost, and a cleanup
          plan you can run yourself.
        </p>
        <p>
          The scanner uses only <strong>read-only AWS APIs</strong> (Describe*, List*, Get*,
          GetMetricStatistics). It never creates, modifies, or deletes anything.
          The Exorcism view generates CLI commands and Terraform hints — you decide whether to run them.
        </p>
      </section>

      <section className="about-section">
        <h3>Privacy guarantee</h3>
        <div className="about-privacy-box">
          <span aria-hidden="true">🔒</span>{" "}
          <strong>No data leaves your browser.</strong> When you drop a custom{" "}
          <code>report.json</code>, it is validated and displayed locally. Nothing is uploaded
          to any server. Graveyard Shift has no backend.
        </div>
      </section>

      <section className="about-section">
        <h3>How to use</h3>
        <ol>
          <li>Install: clone the repo and run <code>make setup</code></li>
          <li>Demo: <code>graveyard scan --demo --out report.json</code></li>
          <li>Live scan: <code>graveyard scan --profile my-profile --regions us-east-1 --out report.json</code></li>
          <li>Open the web app and drop your <code>report.json</code> in.</li>
        </ol>
        <p>
          Cost figures are <strong>estimates</strong> from a bundled price table (last updated 2025-07-01).
          The demo uses synthetic data labelled "Sample Data".
        </p>
      </section>

      <section className="about-section">
        <h3>Detection thresholds (defaults)</h3>
        <table className="about-table">
          <thead>
            <tr>
              <th scope="col">Config key</th>
              <th scope="col">Default</th>
              <th scope="col">Description</th>
            </tr>
          </thead>
          <tbody>
            {THRESHOLDS.map(({ key, default: def, description }) => (
              <tr key={key}>
                <td><code>{key}</code></td>
                <td>{def}</td>
                <td>{description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="about-section">
        <h3>Required IAM policy</h3>
        <p>Attach this read-only policy to the IAM user or role running the scanner:</p>
        <div className="about-policy-header">
          <CopyButton text={IAM_POLICY} label="Copy Policy" />
        </div>
        <pre className="about-code">{IAM_POLICY}</pre>
      </section>

      <section className="about-section about-footer">
        <a
          href="https://github.com/madhura/graveyard-shift"
          target="_blank"
          rel="noopener noreferrer"
          className="about-link"
        >
          View on GitHub →
        </a>
        <span className="about-kiroween">🎃 Kiroween 2026 — Costume Contest entry</span>
      </section>
    </div>
  );
}
