# Shell Scripts
## nas_copier
- Copies source paths listed one row at a time in input file over to a destination path

How to use it
Save the code into a file named nas_copier.sh.

Open your Terminal and make the script executable by running:

```Bash
`chmod +x nas_copier.sh`
Run it using the same flags as the Python script:

```Bash
`./nas_copier.sh -l files_to_copy.txt -s /Volumes/MyExternalDrive -d /Volumes/MyNAS/Backup`
