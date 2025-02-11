# An app builds for data extraction and sending request to AIA's API
## Create your environment
The environment to get this tool running is saved under ```environment.yml```.

To create the environment and install all the package associate with it 
use the code below in your terminal:

```bash
conda env create -f environment.yml
```

After installing, you can check if there is an environment created or not by:

```bash
conda env list
```

There will be an environment called ```AIA_API``` (always).

## Execute the tool

First, navigate to the folder where you save or clone the git repository by using the ```cd``` command:

```bash
cd File/path/to/your/git/repository
```
Or navigate it in the file explorer and copy the file path and paste into the command line

To run the tool simply, in your terminal, activate your environment:

```bash
conda activate your_environment
```

Then, type:

```bash
streamlit run main.py
```