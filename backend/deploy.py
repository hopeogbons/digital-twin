import os
import shutil
import zipfile
import subprocess


def main():
    print("Creating Lambda deployment package...")

    # Clean up
    if os.path.exists("lambda-package"):
        shutil.rmtree("lambda-package")
    if os.path.exists("lambda-deployment.zip"):
        os.remove("lambda-deployment.zip")

    # Create package directory
    os.makedirs("lambda-package")

    # Install dependencies using Docker with Lambda runtime image
    print("Installing dependencies for Lambda runtime...")

    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.getcwd()}:/var/task",
            "--platform",
            "linux/amd64",
            "--entrypoint",
            "",
            "public.ecr.aws/lambda/python:3.12",
            "/bin/sh",
            "-c",
            "pip install --no-cache-dir --target /var/task/lambda-package -r /var/task/requirements.txt",
        ],
        check=True,
    )

    # Copy application files
    print("Copying application files...")
    app_files = ["server.py", "lambda_handler.py", "context.py", "resources.py"]
    for file in app_files:
        if os.path.exists(file):
            shutil.copy2(file, "lambda-package/")
            print(f"  - {file}")

    # Copy data directory
    if os.path.exists("data"):
        shutil.copytree("data", "lambda-package/data")
        print("  - data/")

    # Create zip
    print("Creating zip file...")
    with zipfile.ZipFile("lambda-deployment.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("lambda-package"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "lambda-package")
                zipf.write(file_path, arcname)

    # Show package size
    size_mb = os.path.getsize("lambda-deployment.zip") / (1024 * 1024)
    print(f"✓ Created lambda-deployment.zip ({size_mb:.2f} MB)")

    if size_mb > 50:
        print("⚠ Warning: File exceeds 50MB. Use S3 upload.")
    else:
        print("✓ Size OK for direct Lambda upload")

    # Cleanup temp folder
    shutil.rmtree("lambda-package")
    print("✓ Cleaned up temporary files")


if __name__ == "__main__":
    main()