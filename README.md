# KSRTC-HyRO: Hybrid AI-based Route Optimizer
This repository contains the proof-of-concept for KSRTC-HyRO, a hybrid AI system designed to optimize bus routes for the Kerala State Road Transport Corporation (KSRTC). The project aims to address financial and operational challenges by leveraging data-driven insights and advanced optimization techniques.

# Problem Statement

The KSRTC faces several systemic issues that impact its sustainability. This project addresses the following key problems:

Financial Losses: A significant portion of revenue is consumed by rising fuel costs, often due to suboptimal routing and scheduling.

Manual Inefficiencies: Reliance on manual scheduling leads to overcrowded buses on some routes while others are underutilized, indicating a lack of a data-driven approach.

Lack of Predictive Analytics: The system currently operates in a reactive mode, unable to forecast passenger demand or anticipate traffic congestion.

# Features

This application provides a comprehensive solution with the following features:

    Data-Driven Backend: Extracts and uses thousands of real, named bus stops from OpenStreetMap data for Kerala.

    Intuitive Web Interface: A user-friendly web app for drivers to build multi-stop routes using an autocomplete search and drag-and-drop reordering.

    Real-World Routing: Integrates a local OSRM (Open Source Routing Machine) server to calculate routes that follow the actual road network, not just straight lines.

    Predictive Analytics: A backend Flask server uses a machine learning model to provide real-time estimates for:

        Expected Passenger Count

        Estimated Fuel Cost

    Interactive Map Visualization: Displays the final, optimized route on a real-world, interactive map using Leaflet.js.

    Developer Tools: Includes a toggle to display all available bus stops on the map for debugging and data validation.

# Tech Stack

    Backend & Data Processing: Python, Flask, Pandas, Scikit-learn, Osmium

    Routing Engine: OSRM, Docker

    Frontend: HTML, Tailwind CSS, JavaScript, Leaflet.js, Awesomplete, SortableJS

# Getting Started

Follow these steps to set up and run the project on your local machine.

    # Prerequisites
    Git
    Python 3 (3.8 or higher)    
    Docker Desktop

1. Clone the Repository

    git clone <your_github_repository_link>
    cd <repository_folder_name>

2. Set Up the Python Environment

    Create a virtual environment
        On Windows:
        python -m venv .venv
        On macOS:
        python3 -m venv .venv

    Activate the environment
        On Windows:
        .venv\Scripts\activate
        On macOS:
        source .venv/bin/activate

    Install all required packages
    pip install -r requirements.txt

3. Set Up the OSRM Routing Server

    Make sure Docker Desktop is running.

    Create a folder in the project root named osrm_data.

    Download the kerala-latest.osm.pbf file from Geofabrik and place it inside the osrm_data folder.

    Run the following three Docker commands one by one. Note: The osrm-contract step can take a long time and requires at least 8GB of RAM allocated to Docker (this can be configured in Docker Desktop settings under Resources).

    For macOS / Linux:

        # $(pwd)` automatically uses your current project directory path
        docker run -t -v "$(pwd)/osrm_data:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/kerala-latest.osm.pbf
        docker run -t -v "$(pwd)/osrm_data:/data" osrm/osrm-backend osrm-contract /data/kerala-latest.osrm
        docker run -t -i -p 5000:5000 -v "$(pwd)/osrm_data:/data" osrm/osrm-backend osrm-routed /data/kerala-latest.osrm

    For Windows (Command Prompt / PowerShell):

        # Replace `%cd%` (for CMD) or `$(pwd)` (for PowerShell) with the full absolute path to your project, e.g., "D:\KSRTC Project"
        docker run -t -v "%cd%\osrm_data:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/kerala-latest.osm.pbf
        docker run -t -v "%cd%\osrm_data:/data" osrm/osrm-backend osrm-contract /data/kerala-latest.osrm
        docker run -t -i -p 5000:5000 -v "%cd%\osrm_data:/data" osrm/osrm-backend osrm-routed /data/kerala-latest.osrm

4. Prepare Project Data

    On Windows:
        python src/extract_bus_stops.py
        python src/train_demand_model.py

    On macOS:
        python3 src/extract_bus_stops.py
        python3 src/train_demand_model.py

# How to Run

You will need three separate terminals running simultaneously. Make sure the Python virtual environment is activated in Terminals 2 and 3.

    Terminal 1: OSRM Server

        Make sure the osrm-routed Docker container (from Step 3.3) is running.

    Terminal 2: Backend API Server

        Run the Flask application. This serves the prediction model.

            On Windows:
            python src/app.py
            On macOS:
            python3 src/app.py

    Terminal 3: Frontend Web Server

        Run Python's simple web server to serve the HTML file.

            On Windows:
            python -m http.server
            On macOS:
            python3 -m http.server


    Access the Application

        Open your web browser (like Safari or Chrome) and navigate to:
        http://localhost:8000/ksrtc_driver_app.html

