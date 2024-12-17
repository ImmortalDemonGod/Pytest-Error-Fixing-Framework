# branch_fixer/add_or_replace_headers.py
import os
import re

def add_or_replace_header(root_dir, base_dir):
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, start=base_dir).replace(os.sep, '/')
                header_line = f"# {relative_path}\n"

                with open(file_path, "r+", encoding="utf-8") as f:
                    content = f.read()

                    # Split content into lines
                    lines = content.splitlines(keepends=True)

                    # Initialize variables
                    insert_at = 0
                    new_content = []
                    header_inserted = False

                    # Regex patterns
                    comment_pattern = re.compile(r'^\s*#.*')
                    import_pattern = re.compile(r'^\s*(import|from)\s+')

                    # Iterate through lines to find where to insert the header
                    for idx, line in enumerate(lines):
                        if comment_pattern.match(line):
                            # Skip existing comment lines (potential headers)
                            continue
                        elif import_pattern.match(line):
                            # Found first import statement
                            insert_at = idx
                            break
                        elif line.strip() == '':
                            # Skip blank lines
                            continue
                        else:
                            # Found non-comment, non-import line
                            insert_at = idx
                            break
                    else:
                        # Reached end of file without finding import or non-comment lines
                        insert_at = len(lines)

                    # Remove existing header comments above the first import or code
                    new_content = lines[:insert_at]

                    # Add the new header
                    new_content.append(header_line)

                    # Ensure there's a newline after the header
                    if not new_content[-1].endswith('\n'):
                        new_content[-1] += '\n'

                    # Add the rest of the content
                    new_content.extend(lines[insert_at:])

                    # Combine the new content
                    updated_content = ''.join(new_content)

                    # Write back to the file only if changes are made
                    if updated_content != content:
                        f.seek(0)
                        f.write(updated_content)
                        f.truncate()
                        print(f"Header updated in: {relative_path}")

if __name__ == "__main__":
    # Specify the base directory from which relative paths should be calculated
    # Assuming 'src' is the base directory
    base_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    target_directory = os.path.abspath('.')  # Assuming script runs from branch_fixer root

    add_or_replace_header(target_directory, base_directory)