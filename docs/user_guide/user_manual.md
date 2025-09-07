# ComBadge User Manual

Complete reference guide for all ComBadge features and capabilities.

## Table of Contents

1. [Interface Overview](#interface-overview)
2. [Request Types](#request-types)
3. [Input Methods](#input-methods)
4. [Approval Workflow](#approval-workflow)
5. [Advanced Features](#advanced-features)
6. [Settings and Preferences](#settings-and-preferences)
7. [Reports and Analytics](#reports-and-analytics)
8. [Troubleshooting](#troubleshooting)

## Interface Overview

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ComBadge Fleet Management Assistant              [_][□][X] │
├─────────────────────────────────────────────────────────────┤
│ File  Edit  View  Tools  Help                    🔗●🔊📊⚙️ │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input Panel                    │  Analysis & Approval      │
│  ┌─────────────────────────────┐│  ┌───────────────────────┐ │
│  │ Type your request here...   ││  │ Intent: Not analyzed  │ │
│  │                             ││  │ Confidence: --        │ │
│  │ [🎤] [📧] [📎] [Examples]   ││  │                       │ │
│  └─────────────────────────────┘│  │ [Analyze] [Approve]   │ │
│                                 │  └───────────────────────┘ │
│  History & Templates            │  AI Reasoning             │
│  ┌─────────────────────────────┐│  ┌───────────────────────┐ │
│  │ Recent:                     ││  │ Processing steps      │ │
│  │ • Vehicle F-123 reserved    ││  │ will appear here      │ │
│  │ • Oil change scheduled      ││  │                       │ │
│  │                             ││  │                       │ │
│  └─────────────────────────────┘│  └───────────────────────┘ │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Status: Connected ● User: john.doe@company.com ● Fleet: HQ  │
└─────────────────────────────────────────────────────────────┘
```

### Status Indicators

| Icon | Meaning | Description |
|------|---------|-------------|
| 🔗● | Connection | Green=Connected, Red=Disconnected, Yellow=Connecting |
| 🔊 | Audio | Audio feedback enabled/disabled |
| 📊 | Analytics | Performance metrics visible |
| ⚙️ | Settings | Configuration panel access |

## Request Types

### 1. Vehicle Reservations

**Purpose**: Book vehicles for specific time periods

**Supported Formats:**
```
"Reserve vehicle [ID] for [date] from [start] to [end]"
"Book [vehicle description] for [purpose] on [date]"
"I need [vehicle type] for [duration] starting [time]"
```

**Examples:**
```
✅ "Reserve vehicle F-123 for tomorrow 2pm-4pm"
✅ "Book the blue BMW sedan for client meeting Friday morning"
✅ "I need any available truck for delivery run next Tuesday"
✅ "Reserve vehicle VIN ending 5678 for sales presentation"
```

**Required Information:**
- Vehicle identifier (ID, description, or VIN)
- Date and time
- Duration or end time

**Optional Information:**
- Purpose/reason
- Contact person
- Special requirements

### 2. Maintenance Scheduling

**Purpose**: Schedule vehicle service and repairs

**Supported Formats:**
```
"Schedule [service type] for vehicle [ID] on [date]"
"Vehicle [ID] needs [maintenance] [timeframe]"
"[Service] due for [vehicle] by [deadline]"
```

**Examples:**
```
✅ "Schedule oil change for vehicle F-123 next Friday"
✅ "Vehicle F-456 needs brake inspection this week"
✅ "Annual service due for all sedans by month-end"
✅ "Emergency transmission repair needed for T-789"
```

**Service Types ComBadge Recognizes:**
- **Routine**: Oil change, tire rotation, inspection
- **Repairs**: Brake work, transmission, engine
- **Scheduled**: Annual service, registration renewal
- **Emergency**: Breakdown, accident damage

### 3. Fleet Status Inquiries

**Purpose**: Get information about vehicles and operations

**Supported Formats:**
```
"What's the status of [vehicle/fleet]?"
"Show me [information type] for [timeframe]"
"List all [criteria] vehicles"
```

**Examples:**
```
✅ "What's the status of vehicle F-123?"
✅ "Show me all available vehicles for next week"
✅ "List vehicles due for maintenance this month"
✅ "How many reservations do we have tomorrow?"
```

**Information Types:**
- Vehicle availability
- Maintenance schedules
- Reservation calendars
- Fleet utilization
- Driver assignments

### 4. Fleet Management Operations

**Purpose**: Add, modify, or remove vehicles from fleet

**Supported Formats:**
```
"Add [vehicle details] to fleet"
"Update [vehicle] [information] to [new value]"
"Remove vehicle [ID] from [reason]"
```

**Examples:**
```
✅ "Add new Tesla Model 3, VIN 5YJ3E1EA1JF123456"
✅ "Update vehicle F-123 mileage to 45,000 miles"
✅ "Remove vehicle T-456 from active fleet - sold"
✅ "Change driver assignment for V-789 to Jane Smith"
```

## Input Methods

### 1. Text Input

**Primary Method**: Type requests directly into the input field

**Features:**
- Auto-complete for vehicle IDs
- Spell checking for maintenance terms
- History recall with ↑/↓ keys
- Multi-line support for complex requests

**Best Practices:**
- Use complete sentences
- Include all relevant details
- Check spelling of technical terms
- Review before submitting

### 2. Voice Input

**Activation**: Click 🎤 microphone button or use hotkey (Ctrl+M)

**Supported Languages:**
- English (US/UK/AU)
- Spanish
- French
- German

**Voice Tips:**
```
🎤 "Reserve vehicle Foxtrot one-two-three for tomorrow two P M"
🎤 "Schedule oil change for vehicle Foxtrot four-five-six next Friday"
```

**Voice Command Structure:**
- Speak clearly and at normal pace
- Spell out vehicle IDs phonetically
- Use "P M" and "A M" for times
- Pause between major phrases

### 3. Email Processing

**Setup**: Forward emails to your ComBadge email address

**Supported Formats:**
- Forwarded fleet requests
- Maintenance notifications
- Reservation requests
- Status update requests

**Email Examples:**
```
Subject: Vehicle Reservation Request
Body: Hi, I need to reserve vehicle F-123 for client meeting tomorrow 2-4pm.

Subject: Maintenance Alert
Body: Vehicle F-456 dashboard shows oil change due. Please schedule.
```

**Processing Behavior:**
- Extracts request from email body
- Identifies sender for permissions
- Shows original email in context
- Processes like normal request

### 4. Template-Based Input

**Access**: Click [Examples] button or Ctrl+T

**Categories:**
- Common Reservations
- Standard Maintenance
- Status Inquiries
- Fleet Operations

**Usage:**
1. Select template category
2. Choose specific template
3. Fill in placeholder values
4. Submit request

## Approval Workflow

### Understanding AI Analysis

When you submit a request, ComBadge shows its analysis:

```
🧠 AI Analysis
┌─────────────────────────────────────────────┐
│ Intent Classification                        │
│ ✓ Vehicle Reservation (Confidence: 94%)     │
│                                             │
│ Entity Extraction                           │
│ • Vehicle ID: F-123 ✓                       │
│ • Date: Tomorrow (March 16) ✓               │
│ • Time: 2:00 PM - 4:00 PM ✓                │
│ • Requestor: john.doe@company.com ✓         │
│                                             │
│ Validation Results                          │
│ ✓ Vehicle exists and available              │
│ ✓ Time slot is open                         │
│ ✓ User has reservation permissions          │
│ ⚠ Overlaps with maintenance window          │
│                                             │
│ Confidence Score: 89% (High)               │
│ Risk Level: Low                             │
│ Recommendation: Proceed with approval       │
└─────────────────────────────────────────────┘
```

### Approval Options

**✅ Approve**: Execute request as analyzed
- Click when everything looks correct
- Request executes immediately
- Confirmation message appears

**✏️ Edit**: Modify before execution
- Opens edit interface
- Change any extracted values
- Re-analyze after changes
- Then approve or reject

**🔄 Regenerate**: Re-analyze the request
- Use if analysis seems wrong
- ComBadge re-processes your input
- May ask clarifying questions
- Shows updated analysis

**❌ Reject**: Cancel the request
- Use if request is incorrect
- Optionally provide reason
- Helps improve future analysis
- Returns to input mode

### Edit Interface

When you click **Edit**, you can modify:

```
📝 Edit Request Details
┌─────────────────────────────────────────────┐
│ Vehicle ID: [F-123        ] [🔍 Browse]     │
│ Date: [Tomorrow     ] [📅 Calendar]         │
│ Start Time: [2:00 PM] [🕐 Time Picker]     │
│ End Time: [4:00 PM  ] [🕐 Time Picker]     │
│ Purpose: [Client meeting      ] (Optional)  │
│ Notes: [                      ] (Optional)  │
│                                             │
│ [Cancel] [Preview Changes] [Apply & Approve]│
└─────────────────────────────────────────────┘
```

**Field Types:**
- **Vehicle ID**: Dropdown with available vehicles
- **Dates**: Calendar picker with availability
- **Times**: Time picker with conflict warnings
- **Text Fields**: Free text with validation

### Confidence Levels and Actions

| Confidence | Color | Recommended Action |
|------------|-------|-------------------|
| 90-100% | 🟢 Green | Safe to approve immediately |
| 80-89% | 🟡 Yellow | Review carefully before approving |
| 70-79% | 🟠 Orange | Edit or regenerate recommended |
| 60-69% | 🔴 Red | Likely needs clarification |
| <60% | ⚫ Gray | Regenerate or rephrase request |

## Advanced Features

### 1. Batch Operations

Process multiple requests in sequence:

```
"For all vehicles in Building A parking lot:
1. Schedule inspection for next week
2. Update mileage from odometer readings
3. Check fuel levels and schedule refueling if below 25%"
```

**Batch Processing:**
- Analyzes each sub-request
- Shows combined approval interface
- Execute all or individually
- Progress tracking for long operations

### 2. Conditional Requests

Create requests with conditions:

```
"If vehicle F-123 is available tomorrow 2pm-4pm, reserve it for client meeting.
Otherwise, find the next available sedan and suggest alternative times."
```

**Conditional Logic:**
- If-then-else processing
- Alternative suggestions
- Automatic fallback options
- Smart scheduling recommendations

### 3. Context-Aware Conversations

ComBadge remembers context within sessions:

```
You: "What's the status of vehicle F-123?"
ComBadge: "F-123 is available, last serviced 2 weeks ago, currently at Building A."

You: "Reserve it for tomorrow afternoon"
ComBadge: [Understands "it" refers to F-123]

You: "Actually, make that Friday instead"  
ComBadge: [Updates reservation to Friday, keeps other details]
```

### 4. Smart Scheduling

**Auto-Optimization:**
- Suggests optimal time slots
- Considers travel time between locations
- Avoids maintenance conflicts
- Groups similar requests

**Example:**
```
You: "Schedule oil changes for vehicles F-123, F-456, and F-789"
ComBadge: "I can schedule these efficiently:
- F-123: Tuesday 9am (30 min)
- F-456: Tuesday 10am (30 min)  
- F-789: Tuesday 11am (30 min)
This groups all services at the same location."
```

## Settings and Preferences

### Access Settings
- Click ⚙️ in toolbar
- Use Ctrl+, (comma) hotkey
- Menu: Tools → Preferences

### General Settings

```
🔧 General Preferences
┌─────────────────────────────────────────────┐
│ Language: [English (US)     ▼]              │
│ Time Zone: [EST (UTC-5)     ▼]              │
│ Date Format: [MM/DD/YYYY    ▼]              │
│ Time Format: [12-hour       ▼]              │
│                                             │
│ ☑ Enable sound notifications               │
│ ☑ Show confidence scores                   │
│ ☑ Auto-save request history               │
│ ☑ Remember window position                │
└─────────────────────────────────────────────┘
```

### AI Behavior Settings

```
🤖 AI Assistant Settings
┌─────────────────────────────────────────────┐
│ Confidence Threshold: [80%] ████████░░      │
│ Auto-approve High Confidence: ☑ Enabled     │
│ Show Reasoning Steps: ☑ Always             │
│                                             │
│ Request Processing:                         │
│ ☑ Enable context awareness                 │
│ ☑ Learn from corrections                   │
│ ☑ Suggest alternatives for conflicts       │
│ ☑ Validate against business rules          │
└─────────────────────────────────────────────┘
```

### Approval Workflow Settings

```
✅ Approval Preferences
┌─────────────────────────────────────────────┐
│ Default Action for High Confidence:         │
│ ○ Always require manual approval            │
│ ● Auto-approve above 90% confidence         │
│ ○ Ask each time                            │
│                                             │
│ Review Time: [30 seconds] before auto      │
│                                             │
│ Require confirmation for:                   │
│ ☑ Vehicle modifications                    │
│ ☑ Bulk operations (>5 items)              │
│ ☑ High-cost services (>$500)              │
│ ☑ Weekend/holiday operations               │
└─────────────────────────────────────────────┘
```

### Notification Settings

```
🔔 Notifications
┌─────────────────────────────────────────────┐
│ Email Notifications:                        │
│ ☑ Reservation confirmations                │
│ ☑ Maintenance reminders                   │
│ ☑ System alerts                           │
│                                             │
│ Desktop Notifications:                      │
│ ☑ Request completed                        │
│ ☑ Approval required                        │
│ ☑ Errors and warnings                     │
│                                             │
│ Sound Alerts: [Chime ▼] [🔊 Test]         │
└─────────────────────────────────────────────┘
```

## Reports and Analytics

### Accessing Reports
- Menu: View → Reports
- Hotkey: Ctrl+R
- Status bar: Click 📊 icon

### Usage Statistics

```
📈 Your ComBadge Usage (Last 30 Days)
┌─────────────────────────────────────────────┐
│ Total Requests: 127                         │
│ Successful: 119 (94%)                       │
│ Edited: 23 (18%)                           │
│ Average Confidence: 87%                     │
│                                             │
│ Request Types:                              │
│ ████████░░ Reservations (68)               │
│ █████░░░░░ Maintenance (31)                │
│ ███░░░░░░░ Status Checks (28)             │
│                                             │
│ Most Active Days: Tue, Wed, Thu             │
│ Peak Hours: 9-11am, 2-4pm                  │
└─────────────────────────────────────────────┘
```

### Performance Metrics

```
⚡ System Performance
┌─────────────────────────────────────────────┐
│ Average Response Time: 1.2 seconds          │
│ Accuracy Rate: 91%                         │
│ Auto-approval Rate: 76%                     │
│                                             │
│ Recent Performance Trend: ↗ Improving      │
│                                             │
│ Your Efficiency:                            │
│ • Time saved vs manual: ~4.2 hours/week    │
│ • Requests per session: 3.7 average        │
│ • Learning curve: 89% proficiency          │
└─────────────────────────────────────────────┘
```

## Keyboard Shortcuts

### Global Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New request |
| `Ctrl+Enter` | Submit request |
| `Ctrl+A` | Approve current |
| `Ctrl+E` | Edit current |
| `Ctrl+R` | Regenerate analysis |
| `Ctrl+J` | Reject request |
| `Esc` | Cancel operation |

### Navigation
| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Focus input field |
| `Ctrl+2` | Focus analysis panel |
| `Ctrl+3` | Focus approval controls |
| `Tab` | Next field/control |
| `Shift+Tab` | Previous field/control |

### History and Templates
| Shortcut | Action |
|----------|--------|
| `↑/↓` | Navigate request history |
| `Ctrl+T` | Open templates |
| `Ctrl+H` | Show full history |
| `Ctrl+F` | Find in history |

### Help and Settings
| Shortcut | Action |
|----------|--------|
| `F1` | Open help |
| `Ctrl+?` | Quick reference |
| `Ctrl+,` | Settings |
| `Ctrl+Shift+D` | Debug info |

## Error Messages and Solutions

### Common Error Messages

**"Vehicle not found or not available"**
- **Cause**: Vehicle ID doesn't exist or is inactive
- **Solution**: Check vehicle ID spelling, try vehicle search
- **Prevention**: Use vehicle picker or auto-complete

**"Insufficient permissions for this operation"**
- **Cause**: User account lacks required permissions
- **Solution**: Contact administrator for access
- **Prevention**: Check permissions in user settings

**"Time conflict with existing reservation"**
- **Cause**: Requested time overlaps with existing booking
- **Solution**: Choose different time or vehicle
- **Prevention**: Check availability before requesting

**"Maintenance window conflict"**
- **Cause**: Requested time conflicts with scheduled maintenance
- **Solution**: Reschedule or choose different vehicle
- **Prevention**: Review maintenance calendar

### System Messages

**"Low confidence in request interpretation"**
- **Meaning**: ComBadge is unsure about your request
- **Action**: Add more details or rephrase
- **Example**: Change "fix the car" to "schedule brake repair for vehicle F-123"

**"Multiple possible interpretations"**
- **Meaning**: Request could mean different things
- **Action**: Be more specific about your intent
- **Example**: Clarify "service" as "oil change" or "inspection"

## Integration Features

### Calendar Integration
- Sync with Outlook/Google Calendar
- Show conflicts in scheduling
- Block out maintenance windows
- Export reservations to calendar

### Email Integration  
- Automatic email confirmations
- Maintenance reminders
- Reservation updates
- Status notifications

### Mobile Access
- Responsive web interface
- Mobile app available
- Voice input optimized
- Offline request queuing

---

*For additional help, press F1 in the application or contact your system administrator.*