#!/bin/bash


#run with update message and version for example:
#cd /home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_interface

#./git_automation.sh -m "Refactored modules and added listener.py" -v v0.1


# Function to display usage
usage() {
    echo "Usage: $0 -m <commit-message> -v <version-tag>"
    echo "Example: $0 -m \"Refactored gui module and added system valve control signalling\" -v v0.1"
    exit 1
}

# Parse command line arguments
while getopts ":m:v:" opt; do
    case $opt in
        m) commit_message="$OPTARG" ;;
        v) version_tag="$OPTARG" ;;
        *) usage ;;
    esac
done

# Check if both commit message and version tag are provided
if [ -z "$commit_message" ] || [ -z "$version_tag" ]; then
    usage
fi

# Navigate to the project directory
cd /home/sybednar/FPLC_controller_venv/FPLC_server/FPLC_interface || { echo "Directory not found"; exit 1; }

# Stage the files
git add main.py gui.py method_editor.py network.py data_analysis.py data_logger.py plotting.py listener.py git_automation.sh

# Commit the changes
git commit -m "$commit_message"

# Push the changes to GitHub
git push origin master

# Check if the tag already exists
if git rev-parse "$version_tag" >/dev/null 2>&1; then
    echo "Tag $version_tag already exists. Skipping tagging."
else
    # Tag the commit
    git tag "$version_tag" -m "$commit_message"
    git push origin "$version_tag"
fi

echo "Changes have been pushed and tagged with version $version_tag"
