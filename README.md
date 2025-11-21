# Zscaler URL Filtering Automation with Ansible Semaphore

🚀 **Production-ready automation for Zscaler URL filtering management**

## 📋 Features

✅ **List all URL filtering rules** with status, action, and details  
✅ **Add URL categories** to existing policies  
✅ **Block URLs** by updating rules  
✅ **Update rule actions** (ALLOW, BLOCK, CAUTION)  
✅ **Generate reports** in CSV, JSON, or Table format  
✅ **Secure credential management** via Semaphore environment variables  
✅ **Interactive Surveys** in Semaphore UI for easy operation  

---

## 🏗️ Architecture

```
GitHub Repository
       ↓
Ansible Semaphore (Auto-clone on run)
       ↓
Ansible Playbook (zscaler_playbook.yml)
       ↓
Python Script (zscaler_url_automation.py)
       ↓
Zscaler ZIA API
       ↓
Generate Reports (CSV/JSON/Table)
```

---

## 📁 Repository Structure

```
zscaler-automation/
├── zscaler_url_automation.py       # Main Python script
├── zscaler_playbook.yml            # Ansible playbook
├── requirements.txt                # Python dependencies
├── reports/                        # Generated reports directory
│   ├── zscaler_rules_20241121_143022.csv
│   └── zscaler_rules_20241121_143022.json
└── README.md                       # This file
```

---

## 🔧 Setup Instructions

### **Step 1: Push Code to GitHub**

1. Create a new repository (e.g., `zscaler-automation`)
2. Add all files:
   ```bash
   git init
   git add .
   git commit -m "Initial Zscaler automation setup"
   git branch -M main
   git remote add origin https://github.com/YOUR-ORG/zscaler-automation.git
   git push -u origin main
   ```

### **Step 2: Configure Ansible Semaphore**

#### A. Add Repository
1. Go to **Repositories** in Semaphore
2. Click **New Repository**
3. Fill in:
   - **Name**: `Zscaler Automation`
   - **URL**: `https://github.com/YOUR-ORG/zscaler-automation.git`
   - **Branch**: `main`
   - **Access Key**: (if private repo, add SSH key or token)

#### B. Create Key Store (Secrets)
1. Go to **Key Store**
2. Add the following secrets:

   **Secret 1: Zscaler Password**
   - **Name**: `zscaler_password`
   - **Type**: `Login with Password`
   - **Username**: (leave blank or use dummy value)
   - **Password**: `YOUR_ZSCALER_PASSWORD`

   **Secret 2: Zscaler API Key**
   - **Name**: `zscaler_api_key`
   - **Type**: `Login with Password`
   - **Username**: (leave blank)
   - **Password**: `YOUR_ZSCALER_API_KEY`

#### C. Create Environment
1. Go to **Environment**
2. Click **New Environment**
3. Name: `Zscaler Production`
4. Add environment variables (JSON format):
   ```json
   {
     "ZSCALER_CLOUD": "zscalerbeta",
     "ZSCALER_USERNAME": "admin@yourcompany.com",
     "ZSCALER_PASSWORD": "{{ zscaler_password }}",
     "ZSCALER_API_KEY": "{{ zscaler_api_key }}"
   }
   ```

#### D. Create Task Template with Surveys

1. Go to **Task Templates**
2. Click **New Template**
3. Fill in basic info:
   - **Name**: `Zscaler URL Filtering Management`
   - **Playbook filename**: `zscaler_playbook.yml`
   - **Repository**: Select your repository
   - **Environment**: Select `Zscaler Production`

4. **Add Survey Fields** (User Inputs):

   **Survey 1: Operation Type**
   - Variable Name: `operation`
   - Title: `Operation`
   - Type: `Enum` (dropdown)
   - Options:
     ```
     list
     add-category
     block-url
     update-action
     ```
   - Default: `list`
   - Required: Yes

   **Survey 2: Rule Name**
   - Variable Name: `rule_name`
   - Title: `Rule Name`
   - Type: `String`
   - Description: `Name of the policy rule (e.g., "Block Social Media")`
   - Required: No

   **Survey 3: URL to Block**
   - Variable Name: `url_to_block`
   - Title: `URL to Block`
   - Type: `String`
   - Description: `Website to block (e.g., badsite.com)`
   - Required: No

   **Survey 4: URL Category**
   - Variable Name: `url_category`
   - Title: `URL Category to Add`
   - Type: `String`
   - Description: `Category like STREAMING_MEDIA, SOCIAL_NETWORKING`
   - Required: No

   **Survey 5: Rule Action**
   - Variable Name: `rule_action`
   - Title: `Rule Action`
   - Type: `Enum`
   - Options:
     ```
     ALLOW
     BLOCK
     CAUTION
     ```
   - Required: No

   **Survey 6: Report Format**
   - Variable Name: `report_format`
   - Title: `Report Format`
   - Type: `Enum`
   - Options:
     ```
     table
     csv
     json
     ```
   - Default: `table`
   - Required: No

5. Save the template

---

## 🎮 Usage Examples

### **Example 1: List All Rules**

1. Go to Task Templates
2. Click **Run** on "Zscaler URL Filtering Management"
3. In the Survey popup:
   - Operation: `list`
   - Report Format: `table` (or `csv` for export)
4. Click **Run**

**Output:**
```
================================================================================
ID         Name                           State      Action     Order  
================================================================================
123456     Block Social Media             ENABLED    BLOCK      1      
123457     Allow Finance Apps             ENABLED    ALLOW      2      
123458     Caution on Streaming           ENABLED    CAUTION    3      
================================================================================
📊 Total Rules: 3
✅ Enabled: 3
❌ Disabled: 0
```

---

### **Example 2: Add URL Category to Existing Rule**

**Scenario:** Add "STREAMING_MEDIA" category to "Block Social Media" rule

1. Click **Run**
2. Survey inputs:
   - Operation: `add-category`
   - Rule Name: `Block Social Media`
   - URL Category: `STREAMING_MEDIA`
3. Click **Run**

**Output:**
```
✅ Found rule: Block Social Media (ID: 123456)
📝 Adding category 'STREAMING_MEDIA' to rule 'Block Social Media'
✅ Successfully added category to rule 'Block Social Media'
   Previous categories: SOCIAL_NETWORKING
   Updated categories: SOCIAL_NETWORKING, STREAMING_MEDIA
```

---

### **Example 3: Block a URL**

**Scenario:** Block "malicious-site.com"

1. Click **Run**
2. Survey inputs:
   - Operation: `block-url`
   - Rule Name: `Block Malicious Sites`
   - URL to Block: `malicious-site.com`
3. Click **Run**

**Output:**
```
🚫 Attempting to block URL: malicious-site.com
✅ Found rule: Block Malicious Sites (ID: 123459)
📝 Changing rule action to BLOCK
✅ Rule 'Block Malicious Sites' action set to BLOCK

⚠️  Manual step required:
   1. Go to Zscaler Admin > URL & Cloud App Control > Custom Categories
   2. Add 'malicious-site.com' to a custom category
   3. Assign that category to rule 'Block Malicious Sites'
```

---

### **Example 4: Update Rule Action**

**Scenario:** Change "Allow Finance Apps" from ALLOW to CAUTION

1. Click **Run**
2. Survey inputs:
   - Operation: `update-action`
   - Rule Name: `Allow Finance Apps`
   - Rule Action: `CAUTION`
3. Click **Run**

**Output:**
```
✅ Found rule: Allow Finance Apps (ID: 123457)
📝 Updating rule 'Allow Finance Apps' action to 'CAUTION'
✅ Rule action updated successfully
   Previous action: ALLOW
   New action: CAUTION
```

---

### **Example 5: Generate CSV Report**

1. Click **Run**
2. Survey inputs:
   - Operation: `list`
   - Report Format: `csv`
3. Click **Run**

**Output:**
```
✅ Found 15 URL filtering rules
📄 Report saved: reports/zscaler_rules_20241121_143022.csv
```

**CSV Content:**
```csv
id,name,state,action,order,rank,description,url_categories,protocols,locations,groups,users
123456,Block Social Media,ENABLED,BLOCK,1,7,Blocks social networks,SOCIAL_NETWORKING,HTTPS,5,2,0
123457,Allow Finance Apps,ENABLED,ALLOW,2,7,Banking sites,FINANCE,HTTPS,3,1,10
```

---

## 🗓️ Scheduling (Optional)

To run automatically (e.g., daily compliance report):

1. In Task Template, enable **Schedule**
2. Set **Cron Expression**:
   - Daily at 8 AM: `0 8 * * *`
   - Every Monday at 9 AM: `0 9 * * 1`
   - Every 6 hours: `0 */6 * * *`
3. Set Survey defaults:
   - Operation: `list`
   - Report Format: `csv`

---

## 🔍 Troubleshooting

### **Error: "Missing environment variables"**
**Solution:**
- Check Semaphore Environment variables are set correctly
- Verify Key Store secrets are referenced properly
- Ensure format: `{{ secret_name }}`

### **Error: "Zscaler SDK not installed"**
**Solution:**
The playbook auto-installs dependencies. If it fails:
```bash
# SSH to Semaphore runner
pip3 install -r requirements.txt
```

### **Error: "Failed to authenticate"**
**Solution:**
- Verify Zscaler credentials in Key Store
- Check cloud name (zscaler, zscalertwo, zscalerbeta, etc.)
- Test API access manually:
  ```bash
  curl -X POST "https://admin.zscalerbeta.net/api/v1/authenticatedSession" \
    -H "Content-Type: application/json" \
    -d '{"username":"YOUR_USER","password":"YOUR_PASS","apiKey":"YOUR_KEY"}'
  ```

### **Error: "Rule not found"**
**Solution:**
- Rule names are case-sensitive
- Use exact name as shown in `list` operation
- Check for typos or extra spaces

### **Reports not saving**
**Solution:**
- Ensure `reports/` directory exists in repository
- Check Semaphore runner has write permissions
- View logs: Semaphore → Task History → View Logs

---

## 📊 Common URL Categories

```
SOCIAL_NETWORKING          # Facebook, Twitter, LinkedIn
STREAMING_MEDIA            # YouTube, Netflix, Spotify
GAMBLING                   # Casino, betting sites
ADULT_THEMES              # Adult content
MALWARE_SITES             # Known malicious sites
PHISHING                  # Phishing attempts
PROXY_AVOIDANCE          # VPN, proxy sites
FILE_SHARING             # Dropbox, torrents
GAMING                   # Online games
SHOPPING                 # E-commerce sites
FINANCE                  # Banking, investment
EDUCATION                # Educational sites
NEWS_MEDIA              # News websites
```

**Full list:** https://help.zscaler.com/zia/url-categories

---

## 🔐 Security Best Practices

1. ✅ **Never commit credentials to GitHub**
   - Always use Semaphore Key Store
   - Add `.env` to `.gitignore`

2. ✅ **Use least privilege**
   - Create dedicated Zscaler API admin account
   - Grant only necessary permissions

3. ✅ **Audit logs**
   - Review Semaphore task history regularly
   - Enable Zscaler admin activity logs

4. ✅ **Test in non-production first**
   - Create separate Zscaler sandbox
   - Test all operations before production use

5. ✅ **Version control everything**
   - Keep playbooks and scripts in Git
   - Use branches for changes
   - Require code reviews

---

## 📞 Support

**For issues with:**
- **Ansible Semaphore:** Check [Semaphore Docs](https://www.ansible-semaphore.com/docs/)
- **Zscaler API:** Check [Zscaler API Docs](https://help.zscaler.com/zia/api)
- **Python SDK:** Check [SDK GitHub](https://github.com/zscaler/zscaler-sdk-python)

**Need help?**
- Review task logs in Semaphore → Task History
- Check Python script output for detailed errors
- Enable debug mode: Add `--verbose` flag in playbook

---

## 🎓 Next Steps

1. ✅ Test `list` operation first
2. ✅ Verify report generation works
3. ✅ Test `add-category` on a non-critical rule
4. ✅ Set up scheduled compliance reports
5. ✅ Create additional templates for common tasks
6. ✅ Integrate with ticketing systems (ServiceNow, Jira)

---

## 📝 Changelog

**v2.0** (2024-11-21)
- Added survey-based UI for operations
- Implemented CSV/JSON report generation
- Added comprehensive error handling
- Multiple operation modes
- Production-ready logging

**v1.0** (Initial)
- Basic list and block functionality

---

**Built with ❤️ by Network Automation Team**
