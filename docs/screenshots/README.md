# Documentation screenshot plan

Copy approved screenshots into this folder using the names below. The screenshots
provided in chat are not automatically repository files, so rename and add them
manually before uncommenting any image references in the main README.

| Filename | Capture | Insert after | Suggested alt text |
|---|---|---|---|
| `01-foundry-agents-list.png` | Foundry Agents list showing the four running agents | README → What is working | Four running MMAUG role agents in Microsoft Foundry |
| `02-admin-agent-playground.png` | `mmaug-admin` playground showing model, instructions and File Search | Agent guide → Agent definitions | Admin agent instructions and File Search tool |
| `03-admin-file-search-knowledge.png` | Attach files dialog showing a completed vector-index upload | Agent guide → Knowledge ingestion | Completed administrator knowledge upload to File Search |
| `04-admin-agent-details.png` | Agent Details showing Running, active version and Responses endpoint | Agent guide → Endpoint and identity | Running admin agent and active Responses endpoint |
| `05-foundry-traces.png` | Traces page; recapture after Application Insights is connected | Agent guide → Monitoring | Foundry trace and conversation monitoring |
| `06-public-assistant-drawer.png` | Landing page with bottom-right Ask MMAUG drawer open | README → Public landing page | Public visitor assistant on the landing page |
| `07-role-dashboard-assistant.png` | A signed-in dashboard with My assistant drawer open | README → Signed-in dashboards | Role-aware assistant in a signed-in dashboard |
| `08-managed-identity-rbac.png` | IAM view showing Contributor and Foundry User for the UAMI | README → Effective permissions | Managed identity Azure and Foundry role assignments |
| `09-github-deployment-success.png` | Successful Deploy development run and summary | README → Run deployment | Successful infrastructure, agent and application deployment |
| `10-postgresql-user-table.png` | Read-only database table/query result with synthetic rows | Database guide → View the user table | Synthetic user roles stored in PostgreSQL |

## Screenshot rules

1. Crop to the feature being explained.
2. Hide access tokens, secrets, connection strings, passwords and recovery links.
3. Blur personal email addresses unless they are explicitly synthetic demonstration data.
4. Do not expose unrelated subscription or tenant information.
5. Use PNG for portal screenshots and keep each file reasonably compressed.
6. Add a one-sentence caption below each image.
7. Replace `05-foundry-traces.png` after Application Insights is connected; the current
   “No traces” screenshot proves configuration state but not observability.

Example Markdown:

```markdown
![Four running MMAUG role agents in Microsoft Foundry](docs/screenshots/01-foundry-agents-list.png)

*Four persistent prompt agents are running in the Sweden Central project.*
```
