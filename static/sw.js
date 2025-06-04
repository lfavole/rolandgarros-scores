var VERSION = "dev";

self.addEventListener("install", evt => {
	async function init() {
		var keys = await caches.keys();
		for(var key, i = 0, l = keys.length; i < l; i++) {
			key = keys[i];
			if(key == VERSION) continue;
			console.log(`Deleting cache ${key}`);
			caches.delete(key);
		}
		// Create a cache for this version
		console.log(`Opening ${VERSION} cache`);
		await caches.open(VERSION);
	}
	evt.waitUntil(init());
});

self.addEventListener("fetch", async evt => {
	async function fetchFromCache(request) {
		ret = await caches.match(request);
		console.log(`Fetching ${request.url} from cache${ret ? "" : ", does not exist"}`);
		return ret;
	}
	async function getResponse(evt) {
		var request = evt.request;
		// In production, try to get the response from the cache
		// (in development, files change and mustn't be cached)
		if(VERSION != "dev") {
			var cachedResponse = await fetchFromCache(request);
			if(cachedResponse && cachedResponse.status != "opaqueredirect") return cachedResponse;
		}
		try {
			var response = await fetch(request);

			if(response.ok && !response.url.includes("polling")) {
				// Store the response in the version cache
				var clonedResponse = response.clone();

				evt.waitUntil(
					caches.open(VERSION)
					.then(cache => {
						console.log(`Storing ${response.url}`);
						return cache.put(request, clonedResponse);
					})
					.catch(console.error)
				);
			}

			return response;
		} catch(err) {
			// In development, serve requests from the cache if they couldn't be done
			if(VERSION == "dev") {
				var cachedResponse = await fetchFromCache(request);
				if(cachedResponse)
					return cachedResponse;
				else
					throw err;
			}
		}
	}
	evt.respondWith(getResponse(evt));
});
