// Copyright (c) 2023 Synology Inc. All rights reserved.

class ReqUtils {
	#browser = MediaSource?.isTypeSupported('audio/mpeg;') ? '' : '&browser=0';
	#url = Object.freeze({
		login: 'https://{0}:{1}/webapi/SurveillanceStation/ThirdParty/Auth/Login/v1?account={2}&passwd={3}',
		logout: 'https://{0}:{1}/webapi/SurveillanceStation/ThirdParty/Auth/Logout/v1?_sid={2}',
		keepAlive: 'https://{0}:{1}/webapi/SurveillanceStation/Recording/Keepalive/v5?_sid={2}',
		cam: 'https://{0}:{1}/webapi/SurveillanceStation/ThirdParty/Camera/List/v1?_sid={2}',
		wssLive: 'wss://{0}:{1}/ss_webstream_task/?camId={2}{3}&_sid={4}',
		wssRec: 'wss://{0}:{1}/ss_webstream_task/?camId={2}&time={3}{4}&_sid={5}',
		rtspLive: 'rtsp://{0}:554/camId={1}&_sid={2}',
		rtspRec: 'rtsp://{0}:554/camId={1}&time={2}&_sid={3}',
	});
	#emptyInput = Object.freeze({
		ip: '{IP}',
		port: '{Port}',
		usr: '{Username}',
		pwd: '{Password}',
		sid: '{Sid}',
		camId: '{CameraID}',
		time: "{yyyy-MM-dd'T'HH:mm:ss}",
	});
	#formatStr(format, ...args) {
		return format.replace(/\{(\d+)\}/g, (m, i) => args[i]);
	}

	constructor() {
	}
	getLoginUrl({ ip = this.#emptyInput.ip, port = this.#emptyInput.port,
				  usr = this.#emptyInput.usr, pwd = this.#emptyInput.pwd } = this.#emptyInput) {
		return this.#formatStr(this.#url.login, ip, port, usr, pwd);
	}
	getLogoutUrl({ ip, port, sid } = this.#emptyInput) {
		return this.#formatStr(this.#url.logout, ip, port, sid);
	}
	getKeepAliveUrl({ ip, port, sid } = this.#emptyInput) {
		return this.#formatStr(this.#url.keepAlive, ip, port, sid);
	}
	getCamUrl({ ip, port, sid } = this.#emptyInput) {
		return this.#formatStr(this.#url.cam, ip, port, sid);
	}
	getWssUrl({ ip, port, sid, camId, time } = this.#emptyInput) {
		if (time) {
			return this.#formatStr(this.#url.wssRec, ip, port, camId, time, this.#browser, sid);
		} else {
			return this.#formatStr(this.#url.wssLive, ip, port, camId, this.#browser, sid);
		}
	}
	getRtspUrl({ ip, sid, camId, time } = this.#emptyInput) {
		if (time) {
			return this.#formatStr(this.#url.rtspRec, ip, camId, time, sid);
		} else {
			return this.#formatStr(this.#url.rtspLive, ip, camId, sid);
		}
	}
	sendWebapi(url) {
		return fetch(url).then((response) => response.json()).catch((err) => null);
	}
}
