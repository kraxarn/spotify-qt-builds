const getCurrentSystem = () => {
	const userAgent = navigator.userAgent
	if (userAgent.includes("Linux")) {
		return {
			id: "linux",
			name: "Linux",
			ext: ".AppImage",
		}
	}
	if (userAgent.includes("Macintosh")) {
		return {
			id: "macos",
			name: "macOS",
			ext: ".dmg",
		}
	}
	if (userAgent.includes("Windows") && userAgent.includes("x64")) {
		return {
			id: "win64",
			name: "Windows",
			ext: "win64.zip",
		}
	}
	return {
		id: "win32",
		name: "Windows",
		ext: "win32.zip",
	}
}

const getDownloadUrl = async ext => {
	const releases = await fetch("https://api.github.com/repos/kraxarn/spotify-qt-nightly/releases")
	const json = await releases.json()
	const assets = json[0]["assets"]
	for (const asset of assets) {
		if (asset["name"].endsWith(ext)) {
			return asset["browser_download_url"]
		}
	}
	return null
}

const currentSystem = getCurrentSystem()
document.getElementById("system-name").textContent = currentSystem.name
getDownloadUrl(currentSystem.ext).then(url => {
	if (!url) {
		return
	}
	document.getElementById("download").href = url
})