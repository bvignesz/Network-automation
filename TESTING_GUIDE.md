# Testing & Validation Guide

## 🧪 Pre-Production Testing Checklist

Before using this in production, follow these tests in order:

---

## Phase 1: Local Testing (Your Laptop)

### **Test 1: Environment Variables**
```bash
# Set environment variables
export ZSCALER_USERNAME="admin@yourcompany.com"
export ZSCALER_PASSWORD="your_password"
export ZSCALER_API_KEY="your_api_key"
export ZSCALER_CLOUD="zscalerbeta"

# Verify they're set
echo $ZSCALER_USERNAME
```

**Expected:** Your username prints

---

### **Test 2: Install Dependencies**
```bash
pip3 install -r requirements.txt
```

**Expected Output:**
```
Successfully installed zscaler-sdk-python-0.6.0 requests-2.31.0 ...
```

---

### **Test 3: List Rules (Read-Only)**
```bash
python3 zscaler_url_automation.py --list-rules --format table
```

**Expected Output:**
```
🔐 Connecting to Zscaler cloud: zscalerbeta
✅ Successfully authenticated with Zscaler API
📋 Fetching all URL filtering rules...
✅ Found X URL filtering rules

================================================================================
ID         Name                           State      Action     Order  
================================================================================
123456     Block Social Media             ENABLED    BLOCK      1
...
```

**✅ Success Criteria:**
- No authentication errors
- Rules display correctly
- Your actual rules appear

**❌ If it fails:**
- Check credentials
- Verify cloud name
- Check firewall/proxy settings

---

### **Test 4: Export CSV**
```bash
python3 zscaler_url_automation.py --list-rules --format csv
```

**Expected Output:**
```
📄 Report saved: reports/zscaler_rules_TIMESTAMP.csv
```

**Validation:**
```bash
ls -l reports/
cat reports/zscaler_rules_*.csv
```

**✅ Success Criteria:**
- CSV file created
- Contains all rules
- Headers are correct

---

### **Test 5: Find Specific Rule**
```bash
# Replace with YOUR actual rule name
python3 zscaler_url_automation.py --rule-name "Block Social Media" --list-rules
```

**Expected Output:**
```
✅ Found rule: Block Social Media (ID: 123456)
```

---

## Phase 2: Non-Production Write Tests

⚠️ **WARNING:** These tests MODIFY Zscaler config. Use test rules only!

### **Test 6: Create Test Rule in Zscaler**

Before testing updates, create a dedicated test rule:

1. Log into Zscaler Admin Portal
2. Go to: **Policy** → **URL & Cloud App Control** → **URL Filtering Rules**
3. Click **Add Rule**
4. Create test rule:
   ```
   Name: TEST_AUTOMATION_RULE
   Action: CAUTION
   URL Categories: (leave empty for now)
   Locations: All
   State: ENABLED
   ```
5. Click **Save** and **Activate**

---

### **Test 7: Add Category to Test Rule**
```bash
python3 zscaler_url_automation.py \
  --rule-name "TEST_AUTOMATION_RULE" \
  --add-category "STREAMING_MEDIA"
```

**Expected Output:**
```
✅ Found rule: TEST_AUTOMATION_RULE (ID: XXXXX)
📝 Adding category 'STREAMING_MEDIA' to rule 'TEST_AUTOMATION_RULE'
✅ Successfully added category to rule 'TEST_AUTOMATION_RULE'
   Previous categories: 
   Updated categories: STREAMING_MEDIA
```

**Validation:**
1. Log into Zscaler Admin
2. Find TEST_AUTOMATION_RULE
3. Verify STREAMING_MEDIA is now in URL Categories

---

### **Test 8: Update Rule Action**
```bash
python3 zscaler_url_automation.py \
  --rule-name "TEST_AUTOMATION_RULE" \
  --action BLOCK
```

**Expected Output:**
```
📝 Updating rule 'TEST_AUTOMATION_RULE' action to 'BLOCK'
✅ Rule action updated successfully
   Previous action: CAUTION
   New action: BLOCK
```

**Validation:**
1. Check Zscaler Admin
2. Confirm rule action is now BLOCK

---

### **Test 9: Add Another Category**
```bash
python3 zscaler_url_automation.py \
  --rule-name "TEST_AUTOMATION_RULE" \
  --add-category "SOCIAL_NETWORKING"
```

**Expected Output:**
```
✅ Successfully added category to rule 'TEST_AUTOMATION_RULE'
   Previous categories: STREAMING_MEDIA
   Updated categories: STREAMING_MEDIA, SOCIAL_NETWORKING
```

---

## Phase 3: Ansible Playbook Testing

### **Test 10: Ansible Syntax Check**
```bash
ansible-playbook zscaler_playbook.yml --syntax-check
```

**Expected Output:**
```
playbook: zscaler_playbook.yml
```

**✅ Success:** No errors

---

### **Test 11: Dry Run with Ansible**
```bash
ansible-playbook zscaler_playbook.yml \
  -e "operation=list" \
  -e "report_format=table" \
  --check
```

---

### **Test 12: Full Ansible Run (List)**
```bash
ansible-playbook zscaler_playbook.yml \
  -e "operation=list" \
  -e "report_format=table"
```

**Expected Output:**
```
PLAY [Zscaler URL Filtering Automation] **************************************

TASK [List all URL filtering rules] *******************************************
changed: [localhost]

TASK [Display list output] *****************************************************
ok: [localhost] => {
    "msg": [
        "================================================================================",
        "ID         Name                           State      Action     Order",
        ...
    ]
}

PLAY RECAP *********************************************************************
localhost                  : ok=5    changed=1    unreachable=0    failed=0
```

---

### **Test 13: Ansible with Add Category**
```bash
ansible-playbook zscaler_playbook.yml \
  -e "operation=add-category" \
  -e "rule_name=TEST_AUTOMATION_RULE" \
  -e "url_category=GAMBLING"
```

---

## Phase 4: Semaphore Integration Testing

### **Test 14: Semaphore Connection**

1. Open Semaphore UI
2. Go to **Repositories**
3. Find your repo
4. Click **Test Connection**

**✅ Success:** Green checkmark, "Repository is accessible"

---

### **Test 15: Environment Variables in Semaphore**

1. Go to Task Templates → New Task (temporary)
2. Playbook: Create test playbook:
   ```yaml
   ---
   - hosts: localhost
     tasks:
       - debug:
           msg: "Username: {{ lookup('env', 'ZSCALER_USERNAME') }}"
       - debug:
           msg: "Cloud: {{ lookup('env', 'ZSCALER_CLOUD') }}"
   ```
3. Run it
4. Check output shows your values (password will be hidden)

---

### **Test 16: First Real Semaphore Run**

1. Use your actual Task Template
2. Click **Run**
3. Survey inputs:
   - Operation: `list`
   - Report Format: `table`
4. Click **Run**
5. Monitor logs

**✅ Success Indicators:**
- No authentication errors
- Rules list displays
- Task status: SUCCESS

---

### **Test 17: Survey Validation**

Test each operation type:

**A. List with CSV:**
- Operation: `list`
- Report Format: `csv`

**B. Add Category:**
- Operation: `add-category`
- Rule Name: `TEST_AUTOMATION_RULE`
- URL Category: `NEWS_MEDIA`

**C. Update Action:**
- Operation: `update-action`
- Rule Name: `TEST_AUTOMATION_RULE`
- Rule Action: `ALLOW`

---

## Phase 5: Error Handling Tests

### **Test 18: Invalid Credentials**
```bash
export ZSCALER_PASSWORD="wrong_password"
python3 zscaler_url_automation.py --list-rules
```

**Expected Output:**
```
❌ Failed to authenticate: ...
```

**✅ Success:** Script fails gracefully, clear error message

---

### **Test 19: Non-Existent Rule**
```bash
python3 zscaler_url_automation.py \
  --rule-name "THIS_RULE_DOES_NOT_EXIST" \
  --add-category "SOCIAL_NETWORKING"
```

**Expected Output:**
```
⚠️  Rule 'THIS_RULE_DOES_NOT_EXIST' not found
```

---

### **Test 20: Invalid URL Category**
```bash
python3 zscaler_url_automation.py \
  --rule-name "TEST_AUTOMATION_RULE" \
  --add-category "INVALID_CATEGORY_NAME"
```

**Expected Output:**
```
❌ Error updating rule: Invalid URL category
```

---

## Phase 6: Production Readiness Validation

### **Checklist Before Go-Live:**

- [ ] All Phase 1-5 tests passed
- [ ] Test rule created and tested successfully
- [ ] Test rule deleted from Zscaler
- [ ] Semaphore runs complete successfully
- [ ] Reports generate correctly (CSV/JSON)
- [ ] Scheduled tasks configured (if needed)
- [ ] Team trained on Survey inputs
- [ ] Emergency rollback procedure documented
- [ ] Backup of current Zscaler config taken
- [ ] Network team notified of new automation

---

## 🎯 Production First Steps

### **Week 1: Read-Only Operations**
1. Run `list` operation daily
2. Generate CSV reports for team review
3. Verify accuracy of rule data

### **Week 2: Test Category Additions**
1. Identify 1-2 low-risk rules
2. Add categories during maintenance window
3. Verify with team before/after

### **Week 3: Broader Rollout**
1. Add more rules to automation
2. Document standard operating procedures
3. Train additional team members

---

## 📊 Testing Results Template

Use this to track your testing:

```markdown
## Testing Results - [DATE]

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Environment Variables | ✅ | All set correctly |
| 2 | Install Dependencies | ✅ | No errors |
| 3 | List Rules | ✅ | 47 rules found |
| 4 | Export CSV | ✅ | File generated |
| 5 | Find Rule | ✅ | Found test rule |
| 6 | Create Test Rule | ✅ | Rule ID: 123456 |
| 7 | Add Category | ✅ | Category added |
| 8 | Update Action | ✅ | Changed to BLOCK |
| 9 | Add Another Category | ✅ | Now has 2 categories |
| 10 | Ansible Syntax | ✅ | No errors |
| 11 | Ansible Dry Run | ✅ | No issues |
| 12 | Ansible Full Run | ✅ | Completed |
| 13 | Ansible Add Category | ✅ | Category added |
| 14 | Semaphore Connection | ✅ | Connected |
| 15 | Semaphore Env Vars | ✅ | Variables loaded |
| 16 | First Semaphore Run | ✅ | Rules listed |
| 17 | Survey Validation | ✅ | All operations work |
| 18 | Invalid Credentials | ✅ | Error handled |
| 19 | Non-Existent Rule | ✅ | Error handled |
| 20 | Invalid Category | ✅ | Error handled |

**Overall Status:** READY FOR PRODUCTION ✅

**Tested By:** [Your Name]
**Date:** [Date]
**Environment:** Zscaler Beta / Production
```

---

## 🚨 Rollback Procedure

If something goes wrong:

1. **Immediate Action:**
   - Stop all Semaphore tasks
   - Disable scheduled runs

2. **Verify Current State:**
   ```bash
   python3 zscaler_url_automation.py --list-rules --format csv
   ```

3. **Manual Verification:**
   - Log into Zscaler Admin
   - Check recent changes in Audit Logs
   - Policy → Audit → Admin Audit Logs

4. **Restore if Needed:**
   - Use Zscaler Admin UI to manually revert changes
   - If you have backup CSV, use it as reference

---

## 📞 Support During Testing

**Common Issues:**

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Auth fails | Wrong credentials | Double-check Key Store |
| Rule not found | Case sensitivity | Use exact rule name |
| Can't write reports | Permission issue | Check directory permissions |
| Import error | Missing SDK | `pip3 install zscaler-sdk-python` |
| Semaphore task fails | GitHub access | Check repo connection |

---

**Ready for Production?** ✅

Once all tests pass, you're ready to deploy!

Remember: **Start small, test often, automate gradually!** 🚀
