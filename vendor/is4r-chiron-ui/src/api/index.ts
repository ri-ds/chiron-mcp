import config from "../config";

export type HtmlMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export async function APIRequest(method: HtmlMethod, url: string, data?: any) {
  // build the options
  const options: RequestInit = {
    method,
    credentials: "include",
    mode: "cors",
    headers: {
      "Content-Type": "application/json",
    },
  };
  // append on the data if needed
  if (["POST", "PATCH", "PUT"].includes(method)) {
    options["body"] = JSON.stringify(data);
  }

  const state = history.state || {};
  const startTime = Date.now();

  const _paq = (window._paq = window._paq || []);
  // make the request and return the data or response
  try {
    const response = await fetch(`${config.apiBaseUrl}${url}`, options);
    const endTime = Date.now();
    const responseTimeSeconds = (endTime - startTime) / 1000;
    //simple case for if you are suddenly logged out
    if (response.status == 401) {
      _paq.push([
        "trackEvent",
        "API Response (401)",
        "Response Time",
        url.split("?")[0],
        responseTimeSeconds,
      ]);
      window.location.reload();
    }
    if (response.status === 200) {
      const data = await response.json();
      _paq.push([
        "trackEvent",
        "API Response (200)",
        "Response Time",
        url.split("?")[0],
        responseTimeSeconds,
      ]);
      if (data) {
        // return the actual data
        return data;
      }
    } else if (response.status < 400) {
      _paq.push([
        "trackEvent",
        "API Response (<400)",
        "Response Time",
        url.split("?")[0],
        responseTimeSeconds,
      ]);
      // return the response
      return response;
    } else {
      try {
        const data = await response.json();
        _paq.push([
          "trackEvent",
          "API Response (>400)",
          "Response Time",
          url.split("?")[0],
          responseTimeSeconds,
        ]);
        throw Error(data.detail ?? "Error loading data");
      } catch (e: any) {
        console.error(e);
        throw Error("Could not load the page");
      }
    }
  } catch (e: any) {
    const endTime = Date.now();
    const responseTimeSeconds = (endTime - startTime) / 1000;
    _paq.push([
      "trackEvent",
      "Failed to fetch",
      "Response Time",
      url.split("?")[0],
      responseTimeSeconds,
    ]);

    // if the error is thrown by the fetch call itself, then could be because you logged out in a separate window
    // reloading the page will reset and redirect to the set login page.
    // however, this also matches all other fetch errors, so to prevent infinite reloads we retry the call twice
    if (e.name == "TypeError" && e.message == "Failed to fetch") {
      let reloadCount = state.reloadCount || 0;
      if (reloadCount < 3) {
        state.reloadCount = ++reloadCount;
        history.replaceState(state, "", document.URL);
        window.location.reload();
      } else {
        console.error(
          "The page was reloaded 3 times and failed, there may be a connection issue"
        );
        console.log(history.state);
        delete state.reloadCount;

        throw e;
      }
    }
    delete state.reloadCount;

    throw e;
  }
}
export async function APIFileRequest(
  method: HtmlMethod,
  url: string,
  filename: string,
  data?: any
) {
  // build the options
  const options: RequestInit = {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "text/csv",
    },
  };

  // append on the data if needed
  if (["POST", "PATCH", "PUT"].includes(method)) {
    options["body"] = JSON.stringify(data);
  }
  const state = history.state || {};
  try {
    // make the request and return the data or response
    //options.signal = AbortSignal.timeout(120000); //Leaving here for future use.This will solve one minute timeout issues on large file downloads.
    const response = await fetch(`${config.apiBaseUrl}${url}`, options);

    //simple case for if you are suddenly logged out
    if (response.status == 401) {
      window.location.reload();
    }
    if (response.status === 200) {
      const data = await response.text();

      if (data) {
        const newUrl = window.URL.createObjectURL(new Blob([data]));
        const link = document.createElement("a");
        link.href = newUrl;
        link.setAttribute("download", filename); //or any other extension
        document.body.appendChild(link);
        link.click();
      }
    } else if (response.status < 400) {
      // return the response
      return response;
    } else {
      const data = await response.json();
      // check for auth errors and reload
      if (
        !["/me", "/logout"].includes(url) &&
        data?.Message === "UnauthorizedError: Signature has expired"
      ) {
        window.location.reload();
      }

      throw Error(data.detail ?? "Error loading data");
    }
  } catch (e: any) {
    // if the error is thrown by the fetch call itself, then could be because you logged out in a separate window
    // reloading the page will reset and redirect to the set login page.
    // however, this also matches all other fetch errors, so to prevent infinite reloads we retry the call twice
    if (e.name == "TypeError" && e.message == "Failed to fetch") {
      let reloadCount = state.reloadCount || 0;
      if (reloadCount < 3) {
        state.reloadCount = ++reloadCount;
        history.replaceState(state, "", document.URL);
        window.location.reload();
      } else {
        console.error(
          "The page was reloaded 3 times and failed, there may be a connection issue"
        );
        console.log(history.state);
        delete state.reloadCount;
        throw e;
      }
    }
    delete state.reloadCount;
    throw e;
  }
}
