# Getting Started with ComBadge

Welcome to ComBadge! This guide will help you get up and running with the fleet management natural language processor.

## What is ComBadge?

ComBadge is an AI-powered assistant that converts your natural language fleet management requests into precise API calls. Instead of navigating complex fleet management interfaces, simply tell ComBadge what you need in plain English.

**Example:**
- Instead of: *Navigate to Vehicles → Maintenance → Schedule → Select Vehicle F-123 → Set Date → Set Service Type*
- Just say: **"Schedule oil change for vehicle F-123 next Friday"**

## Quick Setup

### 1. First Launch
When you first open ComBadge, you'll see the main interface with three sections:
- **Input Area**: Where you type your requests
- **AI Analysis Panel**: Shows how ComBadge interpreted your request
- **Approval Interface**: Where you review and approve actions

### 2. Basic Configuration
Before making your first request:

1. **Check Connection Status** (green circle = connected)
2. **Verify Your Permissions** (shown in the status bar)
3. **Set Your Preferences** (click Settings ⚙️)

### 3. Your First Request

Let's try a simple vehicle status check:

```
Type: "What's the status of vehicle F-123?"
```

**What happens next:**
1. ComBadge analyzes your request
2. Shows its understanding in the Analysis Panel
3. Presents the planned action for your approval
4. Executes the request when you click "Approve"

## Understanding the Interface

### Input Methods
ComBadge accepts requests in several ways:

**🎤 Voice Input** (if enabled)
- Click the microphone icon
- Speak naturally: "Reserve the blue sedan for tomorrow"

**📧 Email Processing**
- Forward fleet-related emails to ComBadge
- It extracts requests automatically

**💬 Text Input**
- Type directly in the input field
- Use natural language, no special syntax required

### AI Analysis Panel

ComBadge shows you exactly how it interpreted your request:

```
📋 Request Analysis
┌─────────────────────────────────────────┐
│ Intent: Vehicle Reservation             │
│ Confidence: 94%                         │
│                                         │
│ Extracted Information:                  │
│ • Vehicle: F-123                        │
│ • Date: Tomorrow (March 16, 2024)       │
│ • Time: 2:00 PM - 4:00 PM              │
│ • Requestor: john.doe@company.com       │
│                                         │
│ Reasoning:                              │
│ ✓ Clear reservation request             │
│ ✓ Specific vehicle identified           │
│ ✓ Valid time window                     │
│ ✓ All required information present      │
└─────────────────────────────────────────┘
```

### Confidence Scores

ComBadge shows confidence levels for its understanding:

- **🟢 90-100%**: High confidence, likely accurate
- **🟡 70-89%**: Medium confidence, review carefully
- **🟠 50-69%**: Low confidence, consider rewording
- **🔴 <50%**: Very low confidence, needs clarification

## Making Your First Fleet Request

### Example 1: Vehicle Reservation

**Your Request:**
```
"I need to reserve vehicle F-123 for a client meeting tomorrow from 2pm to 4pm"
```

**ComBadge Understanding:**
- **Intent**: Vehicle Reservation
- **Vehicle**: F-123
- **Date**: Tomorrow (March 16, 2024)
- **Time**: 2:00 PM - 4:00 PM
- **Purpose**: Client meeting

**What to Review:**
1. ✅ Vehicle ID is correct
2. ✅ Date and time are accurate
3. ✅ Duration is appropriate
4. Click **"Approve"** to confirm

### Example 2: Maintenance Scheduling

**Your Request:**
```
"Vehicle F-456 needs an oil change scheduled for next Friday morning"
```

**ComBadge Understanding:**
- **Intent**: Maintenance Scheduling
- **Vehicle**: F-456
- **Service**: Oil change
- **Date**: Friday, March 22, 2024
- **Time**: Morning (9:00 AM - suggested)

**What to Review:**
1. ✅ Vehicle ID is correct
2. ✅ Service type is right
3. ⚠️ **Time**: ComBadge suggested 9:00 AM - adjust if needed
4. Edit time if necessary, then **"Approve"**

## Common Request Patterns

### Vehicle Operations
```
"Show me all available vehicles for next week"
"What's the maintenance history for vehicle F-123?"
"Add the new Tesla Model 3 to our fleet"
"Remove vehicle T-456 from active roster"
```

### Reservations
```
"Reserve any available sedan for Monday morning"
"Book vehicle F-123 for sales team from 9am to 2pm tomorrow"
"Cancel my reservation for vehicle V-456"
"Extend my reservation for vehicle F-789 by 2 hours"
```

### Maintenance
```
"Schedule routine service for all vehicles due this month"
"Vehicle F-123 needs emergency brake repair"
"Check if vehicle V-456 is due for inspection"
"Update mileage for vehicle T-789 to 45,000 miles"
```

### Status and Reports
```
"How many vehicles are currently available?"
"Show me all vehicles reserved for next week"
"Generate monthly utilization report for our fleet"
"Which vehicles are overdue for maintenance?"
```

## Tips for Success

### 🎯 Be Specific
- **Good**: "Reserve vehicle F-123 for tomorrow 2-4pm"
- **Avoid**: "I need a car sometime"

### 📅 Use Clear Time References
- **Good**: "Next Friday at 10am", "Tomorrow morning", "March 15th"
- **Avoid**: "Soon", "Later", "In a bit"

### 🚗 Include Vehicle Details
- **Good**: "Vehicle F-123", "The blue BMW sedan", "VIN ending in 5678"
- **Avoid**: "That car", "The one from yesterday"

### ✅ Review Before Approving
Always check:
- Vehicle ID is correct
- Date and time are accurate
- Service details are right
- You have permission for the action

## When Things Don't Work

### Low Confidence Score?
If ComBadge shows low confidence:

1. **Add More Details**: "Vehicle F-123 oil change Friday 10am"
2. **Use Specific Terms**: Say "maintenance" instead of "fix"
3. **Break Down Complex Requests**: Make one request at a time

### Wrong Information Extracted?
Use the **Edit** feature:

1. Click **"Edit"** in the approval panel
2. Correct any mistakes
3. ComBadge learns from your corrections
4. Click **"Approve"** when ready

### Request Rejected?
Common reasons and solutions:

- **Vehicle Not Available**: Try different dates
- **Insufficient Permissions**: Contact your administrator
- **Invalid Time Range**: Check business hours
- **Vehicle Under Maintenance**: Choose alternate vehicle

## Quick Reference Card

### Essential Commands
| Need | Say |
|------|-----|
| **Reserve Vehicle** | "Reserve vehicle [ID] for [date] [time]" |
| **Schedule Service** | "Schedule [service] for vehicle [ID] on [date]" |
| **Check Status** | "What's the status of vehicle [ID]?" |
| **View Available** | "Show available vehicles for [date/time]" |
| **Cancel Reservation** | "Cancel reservation for vehicle [ID]" |

### Time Formats ComBadge Understands
- "Tomorrow at 2pm"
- "Next Friday morning"
- "March 15th from 9am to 3pm"
- "This weekend"
- "End of the week"

### Getting Help
- **F1**: Open help system
- **Ctrl+?**: Quick reference
- **Examples Button**: See sample requests
- **Contact Support**: help@yourcompany.com

## Next Steps

Now that you understand the basics:

1. **📖 Read the [User Manual](user_manual.md)** for complete feature details
2. **🏆 Check [Best Practices](best_practices.md)** for expert tips
3. **🔧 Review [Troubleshooting](troubleshooting.md)** for common issues
4. **❓ Browse the [FAQ](faq.md)** for quick answers

**Ready to dive deeper?** Try our [Basic Workflows Tutorial](../tutorials/basic_workflows.md) for hands-on practice!

---

*Need immediate help? Press **F1** in the application or contact your system administrator.*