
---

## Option 2 — “No data leaks” hardening
If you want to avoid ever committing real numbers, add a sample file pattern:

```bash
cd ~/restaurant_ai_dashboard

# ignore all local data files
printf "\n# local data\n*.json\n!sample_data.json\n" >> .gitignore

# create a sample
cat << 'EOF' > sample_data.json
{
  "platforms": [],
  "vendor_prices": {},
  "maintenance_requests": [],
  "job_postings": [],
  "revenue": [],
  "expenses": []
}
EOF

git add .gitignore sample_data.json
git commit -m "Add sample data and harden .gitignore"
git push
