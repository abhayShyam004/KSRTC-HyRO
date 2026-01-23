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

Follow these simplified steps to set up and run the project on your local machine.

## Prerequisites
- **Git**
- **Python 3** (3.8 or higher)

## 1. Automated Setup
Run the following script to set up the environment:

**`setup_env.bat`**
- Creates a virtual environment.
- Installs all dependencies.

## 2. Run the Application
1.  **Run `run_all.bat`**
    - This will start the application servers.
    - Note: You do NOT need Docker for the main features.
    *(The map routing line may not appear without OSRM/Docker locally, but the app logic, AI predictions, and admin panel will work fully).*

    **OR** manually run:
    ```bash
    python src/app.py
    ```

## 3. Access the App
Open your browser and navigate to:
**http://localhost:5001/ksrtc_driver_app.html**

## Admin Panel
Access at: **http://localhost:5001/login.html**
(Username: `admin`, Password: `vitbp`)

