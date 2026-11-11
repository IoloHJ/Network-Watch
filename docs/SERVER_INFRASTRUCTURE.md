# Server operations

Private deployment records, backup/recovery procedures, inventory and Linux assessment: [NOVA server infrastructure](https://github.com/IoloHJ/nova-server-infrastructure). Filled environments, databases, provider credentials and household state must stay outside source control.

Compose includes Redis PING and web HTTP health checks; the web dependency waits for Redis health and existing PostgreSQL health. These definitions take effect on a future approved container recreation. Existing containers remain running and are monitored by the host watchdog. No database, network-wide DNS or scanner behavior was changed.
