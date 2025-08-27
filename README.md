# Exhibition Controller

Automated 3D object generation system that creates objects from text prompts and displays them in a web viewer.

## Quick Start

1. **Prepare your prompts file**
   - Create a `prompts.csv` file with columns: `Description`, `Material`, `Object`
   - Example:
     ```csv
     Description,Material,Object
     Old,wood,chair
     Broken,metal,table
     Vintage,leather,couch
     ```

2. **Run the system**
   ```bash
   bash START_EXHIBITION.sh
   ```

3. **What happens automatically:**
   - Detects your Point-E and viewer directories
   - Starts generating 3D objects every 30 seconds
   - Opens a web browser to view the results
   - Shows real-time progress

4. **Stop the system**
   - Press `Ctrl+C` in the terminal

## Requirements

- Point-E repository with trained models
- Local 3D viewer directory
- Python environment with required dependencies
- CSV file with prompts

## File Structure

```
exhibition-script/
├── exhibition_controller.py    # Main controller
├── exhibition_config.json      # Configuration
├── prompts.csv                 # Your prompts
├── START_EXHIBITION.sh         # Launch script
└── README.md                   # This file
```

The system will automatically detect your directories and save the configuration for future runs.
