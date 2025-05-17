# i80 LP Management System

A web-based application for managing and viewing Limited Partner (LP) investments across multiple funds, with a focus on transparency and accurate financial calculations.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Features Implementation](#features-implementation)
- [Data Transparency](#data-transparency)
- [SQL Queries for Common Operations](#sql-queries-for-common-operations)

## Architecture Overview

The application follows a modern client-server architecture:

- **Frontend**: React-based single-page application (SPA) with TypeScript
- **Backend**: FastAPI-based Python server with PostgreSQL database
- **Data Flow**: RESTful API endpoints for data retrieval and calculations

## Technology Stack

### Frontend
- React 19.1.0
- TypeScript
- Axios for API calls
- CSS Modules for styling

### Backend
- Python
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- numpy-financial for IRR calculations

## Getting Started

### Single Command Launch

The simplest way to run the entire application is to use the included launcher script:

```bash
# From the project root directory
./run.sh
```

This script:
- Automatically sets up the Python virtual environment if needed
- Starts the backend server at http://localhost:8000
- Starts the frontend development server at http://localhost:3000
- Provides clear status information for both services
- Handles proper shutdown of all components with a single Ctrl+C

### Manual Setup

If you prefer to run components separately:

1. Clone the repository
2. Set up the backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   python init_db.py
   python import_csv.py
   uvicorn main:app --reload
   ```

3. Set up the frontend:
   ```bash
   cd frontend
   npm install
   npm start
   ```

## Project Structure

```
├── backend/
│   ├── models/         # Database models
│   ├── routes/         # API endpoints
│   ├── services/       # Business logic
│   └── main.py        # Application entry point
├── frontend/
│   ├── src/
│   │   ├── components/ # React components
│   │   ├── types/      # TypeScript type definitions
│   │   └── App.tsx    # Root component
└── data/              # CSV data files
```

## Features Implementation

### 1. LP Selection and Basic Information
- Implementation: `LPSelector` component with dropdown menu
- Displays:
  - Status
  - Source
  - First Close Date
  - Inactive Date (if applicable)

### 2. Fund Investment Information
- Implementation: `LPDetails` component showing per-fund metrics
- Key Features:
  - Dynamic date handling based on user-selected Report Date
  - Comprehensive fund details including:
    - Investment dates (First Close, Reinvestment Start, Harvest Start)
    - Fee structure (Management Fee, Incentive Fee)
    - Financial metrics calculated as of Report Date

### 3. Financial Metrics
Each metric is calculated both at the fund level and aggregated across all funds:
- Total Commitment Amount
- Total Capital Called
- Total Capital Distribution
- Total Income Distribution
- Total Distribution
- Remaining Capital Investment

Implementation details:
- Backend calculations in `metrics_calculator.py`
- Data aggregation in `calculate_lp_totals` function
- Frontend display in `LPDetails` component

### 4. IRR Calculation
- Implementation: Custom XIRR calculation matching Excel's methodology
- Includes these cash flows:
  - Capital Calls (negative cash flows) from tbLedger where activity = 'Capital Call'
  - Distributions (positive cash flows) from tbLedger where activity = 'LP Distribution'
  - Ending Capital Balance from tbPCAP as of PCAP Report Date
    - Specifically retrieves only the "Ending Capital Balance" field value from tbPCAP
    - Uses the most recent entry when multiple entries exist (sorted by field_num)
- Calculated at the aggregate LP level across all funds
- Implementation:
  - XIRR formula: `0 = Σ [ CF_i / (1 + IRR)^(d_i/365) ]`
  - Solver: SciPy's Newton method implementation
  - Backend function: `calculate_lp_irr` in metrics_calculator.py
- Cash Flow Convention:
  - Capital calls are recorded as negative values (cash outflow from investor perspective)
  - Distributions and ending balances are recorded as positive values (cash inflow to investor)
  - This convention matches standard finance practice and Excel's XIRR function

### 5. Date Handling
- Report Date:
  - User-selectable via date picker
  - Default: Current date
  - Maximum: Current date
  - Implementation: `LPSelector` component

- PCAP Report Date:
  - Automatically determined based on Report Date
  - Uses maximum fiscal quarter end date from tbPCAP
  - Implementation: `get_pcap_report_date` function

## Data Transparency

We maintain full transparency of calculations through several features:

1. **Interactive Tooltips**
   - Each metric displays an info icon (ⓘ)
   - Hovering shows:
     - Calculation methodology
     - Preview of underlying transactions
     - Option to download full transaction data as CSV

2. **Transaction Data Access**
   - Every financial metric provides access to its underlying transactions
   - Data available in both preview and full download formats
   - CSV exports include all relevant transaction details:
     - Date
     - Activity type
     - Amount
     - Source/Destination entities

3. **Raw Data Structure**
   ```typescript
   interface Transaction {
       effective_date: string;
       activity: string;
       sub_activity: string | null;
       amount: number;
       entity_from: string;
       entity_to: string;
   }
   ```

4. **Database Access**
   - Direct database queries available for advanced users
   - Comprehensive schema documentation
   - Clear relationship mapping between tables

5. **API Documentation**
   - All endpoints documented using FastAPI's automatic Swagger UI
   - Available at `/docs` endpoint
   - Includes request/response schemas and example data

This approach ensures that users can:
- Understand how each metric is calculated
- Verify calculations independently
- Access raw data for custom analysis
- Perform ad-hoc queries as needed

## SQL Queries for Common Operations

### Retrieving First Close Date
The first close date for LPs is stored in the `effective_date` field of the `tbLPLookup` table. Here are examples of how to query this information:

#### SQL Query
```sql
-- Get first close date for a specific LP
SELECT short_name, effective_date AS first_close_date 
FROM tbLPLookup
WHERE short_name = 'LP_NAME';


#### Python Code (using SQLAlchemy)
```python
from sqlalchemy.orm import Session
from backend.db import SessionLocal
from backend.models import tbLPLookup

def get_first_close_date(lp_short_name):
    """Get first close date for a specific LP"""
    db = SessionLocal()
    try:
        lp = db.query(tbLPLookup).filter(tbLPLookup.short_name == lp_short_name).first()
        return lp.effective_date if lp else None
    finally:
        db.close()

def get_all_first_close_dates():
    """Get first close dates for all LPs"""
    db = SessionLocal()
    try:
        lps = db.query(tbLPLookup.short_name, tbLPLookup.effective_date).order_by(tbLPLookup.effective_date).all()
        return [(lp.short_name, lp.effective_date) for lp in lps]
    finally:
        db.close()
```

#### Accessing in the FastAPI Routes
The first close date is already included in the `/api/lp/{short_name}` endpoint response under `lp_details.effective_date`.