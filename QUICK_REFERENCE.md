# 📝 Quick Reference Card - Zscaler Automation

## 🎯 Daily Operations Cheat Sheet

### **Semaphore Survey Quick Guide**

#### Operation: `list`
**What it does:** Shows all URL filtering rules  
**Inputs needed:**
- Report Format: `table` or `csv` or `json`
**Example:** Morning compliance check

---

#### Operation: `add-category`
**What it does:** Adds URL category to existing rule  
**Inputs needed:**
- Rule Name: Exact name (e.g., "Block Social Media")
- URL Category: Category code (e.g., "STREAMING_MEDIA")
**Example:** Block YouTube on Sales team rule

---

#### Operation: `block-url`
**What it does:** Blocks specific URL in a rule  
**Inputs needed:**
- Rule Name: Exact rule name
- URL to Block: Domain (e.g., "badsite.com")
**Example:** Emergency block of malicious site

---

#### Operation: `update-action`
**What it does:** Changes rule action (ALLOW/BLOCK/CAUTION)  
**Inputs needed:**
- Rule Name: Exact rule name
- Rule Action: ALLOW or BLOCK or CAUTION
**Example:** Change Finance rule from BLOCK to ALLOW

---

## 🎨 Common URL Categories

```
✅ MOST USED:
SOCIAL_NETWORKING          Facebook, Twitter, LinkedIn
STREAMING_MEDIA            YouTube, Netflix, Spotify
GAMBLING                   Casino sites
ADULT_THEMES              Adult content
FILE_SHARING              Dropbox, WeTransfer
SHOPPING                  Amazon, eBay
NEWS_MEDIA                News sites
FINANCE                   Banking sites

⚠️ SECURITY:
MALWARE_SITES             Known malware
PHISHING                  Phishing sites
PROXY_AVOIDANCE          VPN, proxies
SPYWARE_ADWARE           Spyware sites

📚 OTHER:
EDUCATION                 Schools, universities
GAMING                   Online games
BUSINESS                 Business sites
GOVERNMENT              Gov websites
```

---

## 🚨 Emergency Procedures

### **Block URL Immediately**
1. Semaphore → Run Task
2. Operation: `update-action`
3. Rule Name: "Emergency Block Rule"
4. Action: BLOCK
5. Then use `block-url` to add domain

### **Generate Urgent Report**
1. Semaphore → Run Task
2. Operation: `list`
3. Report Format: `csv`
4. Download from: `reports/zscaler_rules_TIMESTAMP.csv`

---

## 🔍 Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "Rule not found" | Check exact rule name (case-sensitive) |
| "Auth failed" | Check Semaphore Environment variables |
| "No output" | Check Task History → View Logs |
| "Category invalid" | Use exact category code |

---

## 📞 Quick Contacts

- **Zscaler Admin:** https://admin.YOUR_CLOUD.net
- **Semaphore UI:** http://your-semaphore-url
- **Documentation:** README.md in repo
- **Support:** Your automation team

---

## 💡 Pro Tips

1. **Always run `list` first** to see current state
2. **Use CSV exports** for team reports  
3. **Test in non-prod** rule first
4. **Save rule names** in a text file for easy reference
5. **Schedule daily reports** for compliance

---

**Print this and keep at your desk!** 📌
