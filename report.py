import os
import subprocess

def git_save_changes(commit_message="dev code saved"):
    try:
        # Stage all modified and untracked files
        subprocess.run(["git", "add", "."], check=True)

        # Check if anything is staged (i.e., added to the index)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode == 0:
            print("⚠️ Nothing staged for commit.")
            return False

        # Proceed with commit
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("✅ Git commit completed.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during Git operation: {e}")
        return False


def create_report():
    # Base directory for the project
    base_path = '/home/kdog/pythonprojects/process transcript'

    # Paths to include in the report
    boilerplate_files = [
        os.path.join(base_path, 'instructions.txt'),
        #os.path.join(base_path, 'README.md'),
    ]

    py_files = [
        os.path.join(base_path, 'config.py'),
        os.path.join(base_path, 'alignment.py'),
        os.path.join(base_path, 'formatters.py'),
        os.path.join(base_path, 'pipeline.py'),
        os.path.join(base_path, 'splitters.py'),
        os.path.join(base_path, 'run.py'),
        os.path.join(base_path, 'llm_integration.py'),
        os.path.join(base_path, 'test.py'),
    ]

    txt_files = [
        os.path.join(base_path, 'formatted_transcript.txt'),
        os.path.join(base_path, 'desired_output.txt'),
        os.path.join(base_path, 'transcript.txt'),
    ]

    # Report file path
    report_file = os.path.join(base_path, 'report.txt')

    try:
        with open(report_file, 'w', encoding='utf-8') as report:
            report.write("=== process transcript ===\n\n")

            # DOC section
            for doc_file in boilerplate_files:
                if os.path.exists(doc_file):
                    with open(doc_file, 'r', encoding='utf-8') as f:
                        report.write(f"=== DOCS {os.path.basename(doc_file)} ===\n")
                        report.write(f.read())
                        report.write("\n\n")

            # Python section
            for py_file in py_files:
                if os.path.exists(py_file):
                    with open(py_file, 'r', encoding='utf-8') as f:
                        report.write(f"=== PY {os.path.basename(py_file)} ===\n")
                        report.write(f.read())
                        report.write("\n\n")

            # Data
            for txt_file in txt_files:
                if os.path.exists(txt_file):
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        report.write(f"=== PY {os.path.basename(txt_file)} ===\n")
                        report.write(f.read())
                        report.write("\n\n")

        print(f"✅ Created report at: {report_file}")

        # Call git save after successful report creation
        git_save_changes()

        return True

    except FileNotFoundError as e:
        print(f"❌ File not found: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    create_report()
