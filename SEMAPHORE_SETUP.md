# Semaphore UI Configuration - Quick Reference

## 🔑 Step 1: Key Store Setup

**Location:** Semaphore UI → Key Store → New Key

### **Key 1: Zscaler Password**
```
Name: zscaler_password
Type: Login with Password
Username: (leave blank)
Password: <YOUR_ACTUAL_ZSCALER_PASSWORD>
```

### **Key 2: Zscaler API Key**
```
Name: zscaler_api_key
Type: Login with Password  
Username: (leave blank)
Password: <YOUR_ACTUAL_API_KEY>
```

**⚠️ Important:** 
- Keep these names exact (`zscaler_password`, `zscaler_api_key`)
- They're referenced in the Environment as `{{ zscaler_password }}`

---

## 🌍 Step 2: Environment Setup

**Location:** Semaphore UI → Environment → New Environment

### **Environment Configuration**
```json
{
  "ZSCALER_CLOUD": "zscalerbeta",
  "ZSCALER_USERNAME": "admin@yourcompany.com",
  "ZSCALER_PASSWORD": "{{ zscaler_password }}",
  "ZSCALER_API_KEY": "{{ zscaler_api_key }}"
}
```

**Variable Explanations:**
- `ZSCALER_CLOUD`: Your Zscaler cloud (zscaler, zscalertwo, zscalerthree, zscalerbeta, zscloud, etc.)
- `ZSCALER_USERNAME`: Your admin username/email
- `ZSCALER_PASSWORD`: Reference to Key Store secret
- `ZSCALER_API_KEY`: Reference to Key Store secret

**How to find your cloud:**
- Check your Zscaler admin URL
- `https://admin.zscalerbeta.net` → Cloud is `zscalerbeta`
- `https://admin.zscaler.net` → Cloud is `zscaler`
- `https://admin.zscalertwo.net` → Cloud is `zscalertwo`

---

## 📋 Step 3: Task Template with Surveys

**Location:** Semaphore UI → Task Templates → New Template

### **Basic Configuration**
```
Name: Zscaler URL Filtering Management
Playbook filename: zscaler_playbook.yml
Repository: <Select your GitHub repo>
Environment: <Select Zscaler Production environment>
Inventory: localhost,
```

### **Survey Configuration (User Prompts)**

Copy this JSON into the Survey section:

```json
[
  {
    "name": "operation",
    "title": "Operation",
    "description": "What do you want to do?",
    "type": "enum",
    "values": [
      "list",
      "add-category",
      "block-url",
      "update-action"
    ],
    "default": "list",
    "required": true
  },
  {
    "name": "rule_name",
    "title": "Rule Name",
    "description": "Name of the policy rule (e.g., 'Block Social Media')",
    "type": "string",
    "required": false
  },
  {
    "name": "url_to_block",
    "title": "URL to Block",
    "description": "Website to block (e.g., badsite.com)",
    "type": "string",
    "required": false
  },
  {
    "name": "url_category",
    "title": "URL Category to Add",
    "description": "Category like STREAMING_MEDIA, SOCIAL_NETWORKING",
    "type": "string",
    "required": false
  },
  {
    "name": "rule_action",
    "title": "Rule Action",
    "description": "Action to set on the rule",
    "type": "enum",
    "values": [
      "ALLOW",
      "BLOCK",
      "CAUTION"
    ],
    "required": false
  },
  {
    "name": "report_format",
    "title": "Report Format",
    "description": "How to display/export the results",
    "type": "enum",
    "values": [
      "table",
      "csv",
      "json"
    ],
    "default": "table",
    "required": false
  }
]
```

**If your Semaphore version doesn't support JSON surveys, add them manually:**

#### **Survey 1:**
- Variable Name: `operation`
- Title: `Operation`
- Type: `Enum`
- Options: `list`, `add-category`, `block-url`, `update-action`
- Default: `list`
- Required: ✓

#### **Survey 2:**
- Variable Name: `rule_name`
- Title: `Rule Name`
- Type: `String`
- Required: ☐

#### **Survey 3:**
- Variable Name: `url_to_block`
- Title: `URL to Block`
- Type: `String`
- Required: ☐

#### **Survey 4:**
- Variable Name: `url_category`
- Title: `URL Category to Add`
- Type: `String`
- Required: ☐

#### **Survey 5:**
- Variable Name: `rule_action`
- Title: `Rule Action`
- Type: `Enum`
- Options: `ALLOW`, `BLOCK`, `CAUTION`
- Required: ☐

#### **Survey 6:**
- Variable Name: `report_format`
- Title: `Report Format`
- Type: `Enum`
- Options: `table`, `csv`, `json`
- Default: `table`
- Required: ☐

---

## 🚀 Step 4: Running Your First Task

### **Test 1: List Rules**
1. Go to Task Templates
2. Find "Zscaler URL Filtering Management"
3. Click **Run**
4. In popup:
   - Operation: `list`
   - Report Format: `table`
   - (Leave others blank)
5. Click **Run**
6. Wait for completion
7. Click **Task** → **View Log** to see output

**Expected Output:**
```
================================================================================
ID         Name                           State      Action     Order  
================================================================================
123456     Block Social Media             ENABLED    BLOCK      1      
...
```

### **Test 2: Generate CSV Report**
1. Click **Run** again
2. In popup:
   - Operation: `list`
   - Report Format: `csv`
3. Click **Run**
4. Check logs for: `📄 Report saved: reports/zscaler_rules_TIMESTAMP.csv`

### **Test 3: Add Category to Rule**
1. Click **Run**
2. In popup:
   - Operation: `add-category`
   - Rule Name: `<Name of existing rule>`
   - URL Category: `STREAMING_MEDIA`
3. Click **Run**
4. Check logs for success message

---

## 🔄 Step 5: Setting Up Scheduled Runs (Optional)

**For daily compliance reports:**

1. Edit your Task Template
2. Find **Schedule** section
3. Enable scheduling
4. Set Cron expression:
   - Daily at 8 AM: `0 8 * * *`
   - Every Monday: `0 9 * * 1`
5. Set default Survey values:
   ```json
   {
     "operation": "list",
     "report_format": "csv"
   }
   ```
6. Save

Now reports generate automatically!

---

## 🐛 Troubleshooting Checklist

### **Task fails immediately:**
- [ ] Check Repository is accessible
- [ ] Verify Branch is correct (usually `main` or `master`)
- [ ] Ensure `zscaler_playbook.yml` exists in repo root

### **Authentication errors:**
- [ ] Verify Key Store secrets are created
- [ ] Check Environment references them correctly: `{{ secret_name }}`
- [ ] Confirm ZSCALER_CLOUD matches your admin URL
- [ ] Test credentials manually in Zscaler admin portal

### **Python errors:**
- [ ] Ensure `requirements.txt` is in repo
- [ ] Check Python 3 is installed on Semaphore runner
- [ ] Manually install: `pip3 install zscaler-sdk-python`

### **Survey not showing:**
- [ ] Check Survey JSON is valid
- [ ] Ensure Task Template is saved
- [ ] Try refreshing browser
- [ ] Check Semaphore version supports Surveys (v2.8.90+)

---

## 📧 Email Notifications (Optional)

To get email when tasks complete:

1. Go to Semaphore Settings → Integrations
2. Configure Email/SMTP settings
3. In Task Template → **Notifications**:
   - On Success: ✓
   - On Failure: ✓
   - Recipients: `network-team@company.com`

---

## 🎯 Common Operations Quick Reference

| What You Want | Operation | Required Inputs |
|--------------|-----------|----------------|
| View all rules | `list` | report_format (optional) |
| Export to CSV | `list` | report_format = `csv` |
| Add category to rule | `add-category` | rule_name + url_category |
| Block a URL | `block-url` | rule_name + url_to_block |
| Change rule action | `update-action` | rule_name + rule_action |

---

## 📚 Additional Resources

**Semaphore Docs:**
- [Surveys Documentation](https://docs.ansible-semaphore.com/user-guide/task-templates#surveys)
- [Environment Variables](https://docs.ansible-semaphore.com/user-guide/environment-variables)
- [Scheduling Tasks](https://docs.ansible-semaphore.com/user-guide/task-templates#scheduling)

**Zscaler API:**
- [API Authentication](https://help.zscaler.com/zia/api-getting-started)
- [URL Filtering API](https://help.zscaler.com/zia/url-filtering-api)
- [URL Categories List](https://help.zscaler.com/zia/url-categories)

---

**Last Updated:** November 21, 2024
**Semaphore Version:** 2.9.x
**Python SDK Version:** 0.6.0+
