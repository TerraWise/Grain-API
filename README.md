# An app builds for data extraction and sending request to AIA's API
The environment to get this tool running is saved under weather_stations.py.

To install with the environment use the code below in your terminal:

```bash
    conda env create -f environment.yml
```

If you don't want the environment created to be named 'environment', you can change the filename
to your desired name.

For example, not ~~environment~~ but "AIA_API"

```bash
    conda env create -f AIA_API.yml
```

## Execute the tool
To run the tool simply, in your terminal, activate your environment and type:

```bash
    conda activate your_environment
    streamlit run main.py
```