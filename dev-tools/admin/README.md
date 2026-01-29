# Admin Tools

Utilities intended for administrative maintenance tasks.

- `dev-tools/admin/terminate_req_instances.py`: terminates EC2 instances whose `Name` tag starts with a prefix (default `req-`) in a chosen region, with optional dry-run.
- `dev-tools/admin/list_terminate_active_fleets.py`: lists active EC2 Fleet and Spot Fleet requests in a region (default `eu-west-1`); add `--terminate` to cancel/delete all active fleets found (terminates instances).
