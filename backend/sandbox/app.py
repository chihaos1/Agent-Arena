import logging

from flask import Flask, request, jsonify

from config.logging_config import setup_logging
from executor.sandbox import ReviewerSandbox

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize sandbox
try:
    sandbox = ReviewerSandbox()
    logger.info("Docker sandbox initialized")
except Exception as e:
    logger.error(f"Failed to initialize Docker sandbox: {e}")
    sandbox = None

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""

    logger.debug("Health check requested")
    return jsonify({"status": "healthy"}), 200

@app.route("/execute", methods=["POST"])
def execute():
    """Execute code in a Docker sandbox"""

    try:
        data = request.json

        if not data:
            logger.warning("Empty request body")
            return jsonify({"error": "Empty request body"}), 400

        if 'files' not in data:
            logger.warning("Missing 'files' in request")
            return jsonify({"error": "Missing 'files' in request"}), 400
        
        # Initialize variables
        files = data['files']
        commands = data.get('commands', ['npm install', 'npm run build', 'npm test'])
        workflow_id = data.get('workflow_id', 'unknown')
        repo_name = data.get('repo_name')
        github_token = data.get('github_token')

        # Validate required fields
        if not repo_name:
            logger.warning("Missing 'repo_name' in request")
            return jsonify({"error": "Missing 'repo_name' in request"}), 400
        
        if not github_token:
            logger.warning("Missing 'github_token' in request")
            return jsonify({"error": "Missing 'github_token' in request"}), 400

        # Log request
        logger.info(f"Execution request received")
        logger.info(f"\tWorkflow: {workflow_id}")
        logger.info(f"\tFiles: {len(files)}")
        logger.info(f"\tCommands: {commands}")

        # Execute in sandbox
        result = sandbox.execute(
            generated_files=files,
            commands=commands,
            workflow_id=workflow_id,
            repo_name=repo_name,
            github_token=github_token
        )

        logger.info(f"Execution completed: success={result['success']}")
        
        # Return actual result from sandbox
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("Sandbox Executor Service Starting")
    logger.info("=" * 70)
    logger.info("Port: 5001")
    logger.info("Health Check: http://localhost:5001/health")
    logger.info("Execute Endpoint: http://localhost:5001/execute")
    logger.info("=" * 70)
    
    app.run(host='0.0.0.0', port=5001, debug=True)