// Copyright (c) 2023 Synology Inc. All rights reserved.

const WsPlayer = (function() {

const ERROR_CODE = Object.freeze({
	NONE: 0,
	STREAMING_CLOSED: 1,
	WEBSOCKET_CLOSED: 2,
	UNSUPPORTED_CODEC: 3,
	UNSUPPORTED_MIME: 4,
	WEBSOCKET_URL_ERROR: 5,
});
const MEDIA_TYPE = Object.freeze({
	VIDEO: "1",
	AUDIO: "2",
});

function emptyFunc() {
}

class DataTimer {
	#queue;
	#onTimeUpdate;
	#update(currentTime) {
		const idx = this.#queue.findIndex((data) => (currentTime < data.bufEnd));

		if (0 < idx) {
			const data = this.#queue[idx - 1];

			this.#onTimeUpdate(parseInt(data.timeMs, 10));
			this.#queue.splice(0, idx);
		}
	}

	constructor(onTimeUpdate) {
		this.#queue = [];
		this.#onTimeUpdate = onTimeUpdate;
	}
	getEvtListener() {
		const dataTimer = this;

		return function() {
			dataTimer.#update(this.currentTime);
		};
	}
	add(timeMs, bufEnd) {
		if (0 < bufEnd) {
			this.#queue.push({timeMs, bufEnd});
		}
	}
	reset() {
		this.#queue.length = 0;
	}
}

class MsePlayer {
	#QUEUE_MAX = Object.freeze({
		[MEDIA_TYPE.VIDEO]: 120,
		[MEDIA_TYPE.AUDIO]: 512,
	});
	#MAX_DELAY_LIMIT = 5.0;

	#dom;
	#queue;
	#media;
	#timerId;
	#callbacks;
	#dataTimer;
	#maxDelayTm = 1.0;
	#createMediaSource(mime) {
		if (!MediaSource?.isTypeSupported(mime)) {
			this.#callbacks.onError(ERROR_CODE.UNSUPPORTED_MIME, {mime});
			return;
		}

		const mediaSource = new MediaSource();
		const onSourceOpen = () => {
			mediaSource.removeEventListener('sourceopen', onSourceOpen);
			mediaSource.duration = Infinity;

			this.#media.sourceBuffer = mediaSource.addSourceBuffer(mime);
			this.#media.sourceBuffer.mode = 'sequence';
			this.#media.sourceBuffer.addEventListener('updateend', this.#onUpdateEnd.bind(this));
			this.#media.needData = true;
			this.#media.prevTm = Date.now();
		};

		mediaSource.addEventListener('sourceopen', onSourceOpen);

		return mediaSource;
	}
	#onUpdateEnd() {
		const buffered = this.#getBuffered();
		const now = Date.now();

		if (1000 < Math.abs(now - this.#media.prevTm)) {
			this.#media.prevTm = now;

			if (!this.#dom.paused) {
				this.#reduceDelay(this.#maxDelayTm, buffered);
			}
			if (true === this.#clearBuf(buffered)) {
				return;	/* SourceBuffer.remove triggers updateend */
			}
		}

		this.#dataTimer?.add(this.#media.timeMs, this.#getBufEnd(buffered));
		this.#media.needData = true;
		this.#appendBuf();
	}
	#appendBuf() {
		if ((!this.#media.needData) || (0 === this.#queue.length)) {
			return;
		}

		if ('open' !== this.#media.mediaSource?.readyState) {
			this.#markBad();
			return;
		}

		this.#media.needData = false;
		this.#timerId = setTimeout(() => {
			try {
				const {data, msec, key} = this.#queue.shift();

				this.#media.timeMs = msec;
				if ('1' === key) {
					this.#media.seekEnd = this.#getBufEnd();
				}
				this.#media.sourceBuffer.appendBuffer(data);
			} catch (e) {
				this.#markBad();
			}
		}, 0);	/* setTimeout(0) to avoid blocking Websocket message events */
	}
	#markBad() {
		/* Make player.good() return false, but keep player-dom for new player replacement */
		this.#media.mediaSource = null;
	}
	#clearBuf(buffered) {
		const end = this.#media.seekEnd || this.#getBufEnd(buffered);
		const start = buffered.start(0);

		if (this.#MAX_DELAY_LIMIT < (end - start)) {
			this.#media.sourceBuffer.remove(start, end - 0.5);
			return true;
		}

		return false;
	}
	#reduceDelay(maxDelayTm, buffered = this.#getBuffered()) {
		const end = this.#media.seekEnd || this.#getBufEnd(buffered);
		if (maxDelayTm > (end - this.#dom.currentTime)) {
			return;
		}

		/* delayTm should be min at seeked */
		this.#dom.onseeked = () => {
			delete this.#dom.onseeked;

			const delayTm = this.#getBufEnd() - this.#dom.currentTime;
			this.#maxDelayTm = Math.max(this.#maxDelayTm, delayTm + 0.5);
			this.#maxDelayTm = Math.min(this.#maxDelayTm, this.#MAX_DELAY_LIMIT);
		};
		this.#dom.currentTime = end;
	}
	#getBufEnd(buffered = this.#getBuffered()) {
		return buffered?.end(buffered.length - 1) || 0;
	}
	#getBuffered() {
		try {
			const buffered = this.#media.sourceBuffer.buffered;

			return (0 < buffered.length) ? buffered : void(0);
		} catch (e) {
			return void(0);
		}
	}
	#isQueueMaxReached(msg) {
		if ((MEDIA_TYPE.VIDEO === msg.mediaType) && ("0" === msg.key)) {
			return false; /* Allow clear-queue only when the next I frame is received. */
		}

		return (this.#QUEUE_MAX[msg.mediaType] <= this.#queue.length);
	}
	#clearQueue() {
		clearTimeout(this.#timerId);
		this.#queue = [];
		if (this.#media) {
			this.#media.needData = !!this.#media.sourceBuffer;
		}
	}

	constructor({ mime, blVideo, onError, appendChild, dataTimer }) {
		this.#callbacks = {onError, appendChild};
		this.#dataTimer = dataTimer;
		this.init(mime, blVideo);
	}
	init(mime, blVideo) {
		this.destroy();

		const mediaSource = this.#createMediaSource(mime);
		if (!mediaSource) {
			return;
		}

		const dom = document.createElement((blVideo) ? 'video' : 'audio');
		dom.autoplay = true;
		dom.muted = blVideo;	/* Mute video for chromium autoplay */
		dom.src = URL.createObjectURL(mediaSource);
		dom.ontimeupdate = this.#dataTimer?.getEvtListener();
		this.#callbacks.appendChild(dom);

		this.#dom = dom;
		this.#media.mediaSource = mediaSource;
	}
	append(msg, data) {
		if ((!this.good()) || (!data?.length)) {
			return;
		}

		if (this.#isQueueMaxReached(msg)) {
			this.#clearQueue();
		}
		this.#queue.push({
			data,
			msec: msg.msec,
			key: msg.key,
		});
		this.#appendBuf();
	}
	good() {
		return (this.#media?.mediaSource) ? true : false;
	}
	destroy() {
		if (this.#dom) {
			this.#dom.remove();
			this.#dom = null;
		}
		this.#dataTimer?.reset();
		this.#clearQueue();
		this.#media = {};
	}
	resume() {
		this.#dom?.play();
	}
	pause() {
		this.#dom?.pause();
	}
	flush() {
		this.#clearQueue();
		this.#reduceDelay(0);
	}
	setVolume(volume) {
		if ((this.#dom) && (0 <= volume) && (1 >= volume)) {
			this.#dom.volume = volume;
		}
	}
	setSpeed(speed) {
		if ((this.#dom) && (0 <= speed)) {
			this.#dom.playbackRate = speed;
		}
	}
}

class PlayHandler {
	#MIME = Object.freeze({
		AAC: 'audio/mp4; codecs="mp4a.40.2"',
		MP3: MediaSource?.isTypeSupported('audio/mpeg;') ? 'audio/mpeg;' : 'audio/mp4;',
		AVC1: 'video/mp4; codecs="avc1.42e028"',
		HEV1: 'video/mp4; codecs="hev1.1.6.L93.B0"',
	});

	#prevPlayers;
	#players;
	#callbacks;
	#dataTimer;
	#createPlayer(codec, blVideo) {
		const player = (blVideo) ? this.#createVideo(codec) : this.#createAudio(codec);

		if (player?.good()) {
			this.#players[(blVideo) ? MEDIA_TYPE.VIDEO : MEDIA_TYPE.AUDIO] = player;
		}
	}
	#createVideo(codec) {
		switch (codec.toUpperCase()) {
		case "H265":
			return new MsePlayer(this.#getVideoConfig(this.#MIME.HEV1));
		case "H264":
		case "AVC1":
			return new MsePlayer(this.#getVideoConfig(this.#MIME.AVC1));
		default:
			this.#callbacks.onError(ERROR_CODE.UNSUPPORTED_CODEC, {codec});
			return null;
		}
	}
	#getVideoConfig(mime) {
		return {
			mime,
			...this.#callbacks,
			blVideo: true,
			appendChild: (dom) => {
				this.#addVideoReplaceEvt(dom);
				this.#callbacks.appendChild(dom);
			},
			dataTimer: this.#dataTimer, /* Update time from video only */
		};
	}
	#addVideoReplaceEvt(dom) {
		const evtName = 'canplay';
		const onVideoInit = () => {
			dom.removeEventListener(evtName, onVideoInit);
			this.#destroyPlayers(this.#prevPlayers);
			dom.hidden = false;
		};

		dom.hidden = true;
		dom.addEventListener(evtName, onVideoInit);
	}
	#createAudio(codec) {
		switch (codec.toUpperCase()) {
		case "MP4A-LATM":
		case "MPEG4-GENERIC":
			return new MsePlayer(this.#getAudioConfig(this.#MIME.AAC));
		default:
			return new MsePlayer(this.#getAudioConfig(this.#MIME.MP3));
		}
	}
	#getAudioConfig(mime) {
		return {
			mime,
			...this.#callbacks,
			blVideo: false,
		};
	}
	#forEachPlayer(func) {
		Object.entries(this.#players).forEach(([mediaType, player]) => func(player));
	}
	#destroyPlayers(players) {
		Object.entries(players).forEach(([mediaType, player]) => {
			player.destroy();
			delete players[mediaType];
		});
	}

	constructor({ onError, appendChild, onTimeUpdate }) {
		this.#callbacks = {onError, appendChild};
		this.#dataTimer = new DataTimer(onTimeUpdate);
		this.#prevPlayers = {};
		this.#players = {};
	}
	init(msg) {
		this.#destroyPlayers(this.#prevPlayers);

		if (msg.vdoCodec) {
			this.#prevPlayers = this.#players;
			this.#players = {};
			this.#createPlayer(msg.vdoCodec, true);
		} else {
			this.#destroyPlayers(this.#players);
		}

		if (msg.adoCodec) {
			this.#createPlayer(msg.adoCodec, false);
		}
	}
	destroy() {
		this.#destroyPlayers(this.#players);
		this.#destroyPlayers(this.#prevPlayers);
	}
	append(msg, data) {
		this.#players[msg.mediaType]?.append(msg, data);
	}
	good() {
		return this.#players[MEDIA_TYPE.VIDEO]?.good();
	}
	resume() {
		this.#forEachPlayer((player) => player.resume());
	}
	pause() {
		this.#forEachPlayer((player) => player.pause());
	}
	flush() {
		this.#forEachPlayer((player) => player.flush());
	}
	setVolume(volume) {
		this.#players[MEDIA_TYPE.AUDIO]?.setVolume(volume);
	}
	setSpeed(speed) {
		/* Video speed is controlled from the server, so only need to set the audio speed. */
		this.#players[MEDIA_TYPE.AUDIO]?.setSpeed(speed);
	}
}

class MsgReader {
	#buf;
	#msg;
	constructor() {
		this.#buf = null;
		this.#msg = null;
	}
	read(evt) {
		this.#buf = null;
		this.#msg = null;
		if (!(evt?.data instanceof ArrayBuffer)) {
			return false;
		}

		const buf = new Uint8Array(evt.data);
		if (4 >= buf.length) {
			return false;
		}

		const headerEnd = (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3];
		const header = String.fromCharCode.apply(null, buf.subarray(4, headerEnd));
		const msg = {};

		header.split('&').forEach(function(pair) {
			const keyVal = pair.split('=');

			msg[keyVal[0]] = keyVal[1];
		});

		this.#buf = buf;
		this.#msg = msg;
		this.#msg._end = headerEnd;

		return true;
	}
	isClose() {
		return (!!this.#msg?.close);
	}
	isMediaInfo() {
		return ((this.#msg?.vdoCodec) || (this.#msg?.adoCodec)) ? true : false;
	}
	getMsg() {
		return this.#msg;
	}
	getRawData() {
		return this.#buf?.subarray(this.#msg?._end);
	}
}

class WsHandler {
	#ws;
	#timerId;
	#url;
	#evtFuncs;
	#onOpen = emptyFunc;
	#onClose = emptyFunc;
	#onMessage = emptyFunc;
	#onError;
	#stopKeepAlive() {
		clearTimeout(this.#timerId);
	}
	#startKeepAlive() {
		this.#stopKeepAlive();

		this.#timerId = setTimeout(() => {
			this.send("keepAlive");
			this.#startKeepAlive();
		}, 10000);
	}

	constructor(onError = emptyFunc) {
		this.#onError = onError;
		this.#evtFuncs = {
			onOpen: () => {
				this.#startKeepAlive();
				this.#onOpen();
			},
			onClose: () => {
				this.#stopKeepAlive();
				this.#onClose();
			},
			onMessage: (evt) => this.#onMessage(evt),
		};
	}
	connect({ url, onOpen, onClose, onMessage } = {}) {
		this.#url = url || this.#url;
		this.#onOpen = onOpen || this.#onOpen;
		this.#onClose = onClose || this.#onClose;
		this.#onMessage = onMessage || this.#onMessage;
		this.stop();

		try {
			this.#ws = new WebSocket(this.#url);
			this.#ws.binaryType = "arraybuffer";
			this.#ws.addEventListener('open', this.#evtFuncs.onOpen);
			this.#ws.addEventListener('close', this.#evtFuncs.onClose);
			this.#ws.addEventListener('message', this.#evtFuncs.onMessage);
		} catch (e) {
			this.#onError(ERROR_CODE.WEBSOCKET_URL_ERROR, {url: this.#url});
		}
	}
	stop() {
		this.#stopKeepAlive();

		if (this.#ws) {
			this.#ws.removeEventListener('open', this.#evtFuncs.onOpen);
			this.#ws.removeEventListener('close', this.#evtFuncs.onClose);
			this.#ws.removeEventListener('message', this.#evtFuncs.onMessage);
			this.#ws.close();
			this.#ws = null;
		}
	}
	send(cmd) {
		if (WebSocket.OPEN === this.#ws?.readyState) {
			this.#ws.send(cmd);
		}
	}
}

return class {
	#timerId;
	#wsHandler;
	#reader;
	#player;
	#renderTo = document.body;
	#onError = emptyFunc;
	#onTimeUpdate = emptyFunc;
	#volume = 0.5;
	#speed = 1.0;
	#onMessage(evt) {
		if (!this.#reader.read(evt)) {
			return;
		}
		if (this.#reader.isClose()) {
			this.#onError(ERROR_CODE.STREAMING_CLOSED, this.#reader.getMsg());
			return;
		}

		if (this.#reader.isMediaInfo()) {
			this.#player.init(this.#reader.getMsg());
			this.setVolume(this.#volume);
			this.setSpeed(this.#speed);
		} else {
			this.#player.append(this.#reader.getMsg(), this.#reader.getRawData());
		}

		if (!this.#player.good()) {
			this.#wsHandler.stop();
			this.#timerId = setTimeout(() => this.#wsHandler.connect(), 1000);
		}
	}

	static ERROR_CODE = ERROR_CODE;
	constructor() {
		const onError = (code, msg) => this.#onError(code, msg);
		const appendChild = (dom) => this.#renderTo.appendChild(dom);
		const onTimeUpdate = (timeMs) => this.#onTimeUpdate(timeMs);

		this.#wsHandler = new WsHandler();
		this.#reader = new MsgReader(onError);
		this.#player = new PlayHandler({onError, appendChild, onTimeUpdate});
	}
	play({ url, renderTo, onError, onTimeUpdate } = {}) {
		this.#renderTo = renderTo || this.#renderTo;
		this.#onError = onError || this.#onError;
		this.#onTimeUpdate = onTimeUpdate || this.#onTimeUpdate;

		this.stop();
		this.#wsHandler.connect({
			url,
			onMessage: this.#onMessage.bind(this),
			onClose: () => this.#onError(ERROR_CODE.WEBSOCKET_CLOSED),
		});
	}
	stop() {
		clearTimeout(this.#timerId);
		this.#wsHandler.stop();
		this.#player.destroy();
	}
	resume() {
		this.#player.resume();
		this.#wsHandler.send("pause=false");
	}
	pause() {
		this.#player.pause();
		this.#wsHandler.send("pause=true");
	}
	seek(time) {
		this.#wsHandler.send("time=" + time);
		this.#player.flush();
	}
	setVolume(volume) {
		this.#player.setVolume(volume);
		this.#volume = volume;
	}
	setSpeed(speed) {
		this.#wsHandler.send("speed=" + speed);
		this.#player.setSpeed(speed);
		this.#speed = speed;
	}
};

})();
