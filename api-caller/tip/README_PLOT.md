# Fee Analysis Plotting Tool

This tool visualizes the data collected by the fee monitor, creating plots to analyze max priority fees and gas usage ratios over time.

## Installation Guide

### Installing Python

#### On macOS:
1. Using Homebrew (recommended):
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python
```

2. Or download the installer from [Python's official website](https://www.python.org/downloads/macos/)

### Setting up a Virtual Environment (Recommended for macOS)

1. Navigate to the project directory:
```bash
cd path/to/toolkit/api-caller/tip
```

2. Create a virtual environment:
```bash
python3 -m venv venv
```

3. Activate the virtual environment:
```bash
source venv/bin/activate
```
You should see `(venv)` appear at the beginning of your command prompt.

4. Now install the required packages (while the virtual environment is activated):
```bash
pip install -r requirements.txt
```

5. Verify the installation:
```bash
python -c "import pandas; import matplotlib; import seaborn; print('All packages installed successfully!')"
```

6. When you're done, you can deactivate the virtual environment:
```bash
deactivate
```

To use the script later:
1. Navigate to the project directory:
```bash
cd path/to/toolkit/api-caller/tip
```

2. Activate the virtual environment:
```bash
source venv/bin/activate
```

3. Run the script:
```bash
python plot_fees.py
```

4. Deactivate when done:
```bash
deactivate
```

### Alternative Installation Methods

#### Using pipx (for macOS):
If you prefer not to use a virtual environment, you can use pipx:
```bash
# Install pipx
brew install pipx

# Install the packages
pipx install pandas matplotlib seaborn
```

#### On Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### On Linux (Fedora):
```bash
sudo dnf install python3 python3-pip python3-virtualenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### On Windows:
1. Download the installer from [Python's official website](https://www.python.org/downloads/windows/)
2. Run the installer
3. **Important**: Check "Add Python to PATH" during installation
4. Open Command Prompt and create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Verifying Python Installation

After installation, verify Python is installed correctly:
```bash
# Check Python version
python3 --version
# or
python --version

# Check pip version
pip3 --version
# or
pip --version
```

### Installing Required Packages

1. Open a terminal/command prompt
2. Navigate to the directory containing `requirements.txt`:
```bash
cd path/to/toolkit/api-caller/tip
```

3. Install the required packages:
```bash
# If you have both Python 2 and 3 installed, use pip3
pip3 install -r requirements.txt

# If you only have Python 3 installed
pip install -r requirements.txt
```

4. Verify the installation:
```bash
# Start Python
python3
# or
python

# In the Python interpreter, try importing the packages
>>> import pandas
>>> import matplotlib
>>> import seaborn
>>> exit()
```

If no errors appear, the installation was successful!

## Prerequisites

- Python 3.6 or higher (see installation guide above)
- Required Python packages (install using `pip install -r requirements.txt`):
  - pandas >= 1.5.0
  - matplotlib >= 3.5.0
  - seaborn >= 0.12.0

## Installation

1. Make sure you have Python installed on your system
2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Ensure you have a `fees.csv` file in the same directory as the script. The CSV file should have the following columns:
   - `timestamp`: ISO 8601 formatted timestamp
   - `block_number`: Block number
   - `max_priority_fee_gwei`: Max priority fee in gwei
   - `gas_usage_ratio`: Gas usage ratio (between 0 and 1)

2. Run the script:
```bash
python plot_fees.py
```

3. The script will generate:
   - A file named `fee_analysis.png` containing four plots:
     1. ETH Pattern Max Priority Fee over time
     2. Gas Usage Ratio over time
     3. OP Pattern Max Priority Fee over time
     4. Combined plot with both metrics (dual y-axes)
   - Console output with statistical information about the data

## Output

### Generated Image (`fee_analysis.png`)

The image contains four plots:

1. **ETH Pattern Max Priority Fee Plot** (Top)
   - X-axis: Block Number (formatted with commas)
   - Y-axis: Max Priority Fee (gwei)
   - Blue line showing ETH Pattern eth_maxPriorityFeePerGas trends
   - Title: "ETH Pattern: eth_maxPriorityFeePerGas Over Time"

2. **Gas Usage Ratio Plot** (Second)
   - X-axis: Block Number (formatted with commas)
   - Y-axis: Gas Usage Ratio (%)
   - Red line showing gas usage trends
   - Title: "Gas Usage Ratio Over Time"

3. **OP Pattern Max Priority Fee Plot** (Third)
   - X-axis: Block Number (formatted with commas)
   - Y-axis: Max Priority Fee (gwei)
   - Green line showing OP Pattern eth_maxPriorityFeePerGas (constant at 0.001 gwei)
   - Title: "OP Pattern: eth_maxPriorityFeePerGas Over Time"

4. **Combined Plot** (Bottom)
   - X-axis: Block Number (formatted with commas)
   - Left Y-axis: ETH Pattern Max Priority Fee (gwei) in blue
   - Right Y-axis: OP Pattern Max Priority Fee (gwei) in green
   - Both patterns plotted on the same graph for easy comparison
   - Title: "ETH & OP Pattern: eth_maxPriorityFeePerGas Over Time"
   - Legend showing both patterns ("eth pattern" and "op pattern")

All plots use:
- The 'bmh' style for clean visualization
- Grid lines for better readability
- Block numbers formatted with commas for better readability
- High resolution (300 DPI) output

### Console Output

The script prints the following statistics:
- Total number of blocks analyzed
- Time range of the data
- For Max Priority Fee (gwei):
  - Minimum value
  - Maximum value
  - Mean value
- For Gas Usage Ratio:
  - Minimum value
  - Maximum value
  - Mean value

## Customization

To modify the plots, you can edit the following in `plot_fees.py`:

- Figure size: Change `figsize=(15, 12)` in `plt.figure()`
- Colors: Modify the color codes ('b-' for blue, 'r-' for red)
- Plot style: Change `plt.style.use('seaborn')` to other styles
- Output resolution: Modify `dpi=300` in `plt.savefig()`
- Output format: Change the file extension in `plt.savefig()`

## Example Output

```
Data Statistics:
Total blocks analyzed: 1000
Time range: from 2024-03-21 10:30:00 to 2024-03-21 11:30:00

Max Priority Fee (gwei):
  Min: 1.500
  Max: 2.750
  Mean: 2.125

Gas Usage Ratio:
  Min: 0.450
  Max: 0.850
  Mean: 0.650
```

## Notes

- The script requires the input CSV file to be in the correct format
- The generated image is saved in high resolution (300 DPI)
- The plots use a grid for better readability
- Legends are included for easy identification of metrics
- The combined plot uses different colors and y-axes to distinguish between metrics 