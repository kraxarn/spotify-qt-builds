import json
import os
import sys
import typing
import zipfile

import requests

# Access token needs to be set for GitHub API calls
if "ACCESS_TOKEN" not in os.environ:
	sys.exit("Error: Access token not specified")

access_token = os.environ["ACCESS_TOKEN"]

headers = {
	"Accept": "application/vnd.github.v3+json",
	"Authorization": f"token {access_token}",
}

build_repo_name: typing.Final[str] = "kraxarn/spotify-qt-nightly"
source_repo_name: typing.Final[str] = "kraxarn/spotify-qt"


def get_latest_artifact_url(workflow_id: int) -> str:
	runs_url = f"https://api.github.com/repos/{source_repo_name}/actions/workflows/{workflow_id}/runs"
	runs = requests.get(runs_url, headers=headers) \
		.json()["workflow_runs"]

	artifacts_url = ""
	for run in runs:
		if run["event"] == "push" and run["conclusion"] == "success":
			artifacts_url = run["artifacts_url"]
			break

	if len(artifacts_url) == 0:
		raise ValueError("No artifact found")

	return requests.get(artifacts_url, headers=headers) \
		.json()["artifacts"][0]["archive_download_url"]


def download_file(source: str, target: str):
	with requests.get(source, headers=headers, stream=True) as response:
		with open(target, "wb") as file:
			for chunk in response.iter_content(chunk_size=8192):
				file.write(chunk)


def download_artifact(workflow_id: int, destination: str):
	if "--no-download" in sys.argv and os.path.isfile(destination):
		return
	artifact_url = get_latest_artifact_url(workflow_id)
	download_file(artifact_url, destination)


def extract(file: str) -> str:
	extracted_file: str
	with zipfile.ZipFile(file, "r") as zip_file:
		extracted_file = zip_file.namelist()[0]
		zip_file.extractall()
	return extracted_file


def get_source_hash() -> str:
	return requests.get(f"https://api.github.com/repos/{source_repo_name}/commits", headers=headers) \
		.json()[0]["sha"]


def get_latest_tag(repo: str) -> str:
	return requests.get(f"https://api.github.com/repos/{repo}/tags", headers=headers) \
		.json()[0]["name"]


def get_latest_source_version() -> str:
	tag = get_latest_tag(source_repo_name)
	short_hash = get_source_hash()[0:7]
	return f"{tag}-{short_hash}"


def get_latest_build_version() -> str:
	return get_latest_tag(build_repo_name)


def get_changes(sha: str) -> typing.Generator[str, str, None]:
	commits_url = f"https://api.github.com/repos/{source_repo_name}/commits"
	commits = requests.get(commits_url, headers=headers).json()
	for commit in commits:
		if commit["sha"] == sha:
			break
		yield str(commit["commit"]["message"])


def create_release(version: str, changes: typing.Iterable[str]) -> int:
	data = json.dumps({
		"tag_name": version,
		"name": version,
		"body": "\n".join(changes),
		"prerelease": True,
	})
	releases_url = f"https://api.github.com/repos/{build_repo_name}/releases"
	return requests.post(releases_url, data=data, headers=headers).json()["id"]


def add_release_asset(release_id: int, filename: str):
	assets_url = (
		f"https://uploads.github.com/repos/{build_repo_name}/releases/{release_id}/assets"
		f"?name={filename}"
	)
	upload_headers = headers
	upload_headers["Content-Type"] = "application/octet-stream"
	with open(filename, "rb") as file:
		requests.post(assets_url, headers=upload_headers, data=file)


latest_source = get_latest_source_version()
latest_build = get_latest_build_version()

if latest_source == latest_build and "--force" not in sys.argv:
	print(f"Builds are up-to-date ({latest_build})")
	exit()

print(f"Updating builds to {latest_source}")

# Linux
print("Downloading Linux build")
download_artifact(7734249, "linux.zip")
print("Extracting file")
file_linux = f"spotify-qt-{latest_source}.AppImage"
os.rename(extract("linux.zip"), file_linux)
print(f"Linux build saved to: {file_linux}")

# macOS
print("Downloading macOS build")
download_artifact(18407206, "macos.zip")
print("Extracting file")
file_macos = f"spotify-qt-{latest_source}.dmg"
os.rename(extract("macos.zip"), file_macos)
print(f"macOS build saved to: {file_macos}")

# Windows
print("Downloading Windows builds")
file_win64 = f"spotify-qt-{latest_source}-win64.zip"
file_win32 = f"spotify-qt-{latest_source}-win32.zip"
download_artifact(18195390, file_win64)
download_artifact(18401182, file_win32)
print(f"Windows builds saved to: {file_win64}, {file_win32}")

# Create release
print("Creating release")
release = create_release(latest_source, get_changes(get_source_hash()))
print("Uploading Linux build")
add_release_asset(release, file_linux)
print("Uploading macOS build")
add_release_asset(release, file_macos)
print("Uploading Windows builds")
add_release_asset(release, file_win32)
add_release_asset(release, file_win64)
