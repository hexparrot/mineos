/* webui functions */

function command(data, eventobj) {
	var cmd = $(eventobj.currentTarget).data('cmd');
	var required = $(eventobj.currentTarget).data('required').split(',');
	var params = {cmd: cmd};
	
	$.each(required, function(i,v) {
		reqd = v.replace(/\s/g, '');
		if (reqd in $(eventobj.currentTarget).data())
			params[reqd] = $(eventobj.currentTarget).data(reqd);
		else if (reqd in data)
			params[reqd] = data[reqd];
	})
	
	if (required.indexOf('force') >= 0) 
		params['force'] = true;
	
	console.log(params);
	
	if (required.indexOf('server_name') >= 0) {
		$.getJSON('/server', params)
		.success(function(ret) {
			console.log(ret);
		})
		.fail(function() {

		})
	} else {
		$.getJSON('/host', params)
		.success(function(ret) {
			console.log(ret);
		})
		.fail(function() {
			
		})
	}

}

function model_status(data) {
	var self = this;
	$.extend(self, data);
	
	self.mem_utilization = ko.computed(function() {
		return '{0} / {1}'.format(self.memory, self.java_xmx);
	})
	
	self.capacity = ko.computed(function() {
		return '{0} / {1}'.format(self.players_online, self.max_players);
	})
	
	self.overextended = ko.computed(function() {
		try {
			return parseInt(self.memory) > parseInt(self.java_xmx)
		} catch (err) {
			return false;
		}
	})
}

function viewmodel_status() {
	var self = this;
	self.pings = ko.observableArray();
	self.action = command;

	self.get_pings = function() {
		$.getJSON('/vm/status')
		.success(function(data){
			$.each(data, function(i,v) {
				self.pings.push(new model_status(v));
			})
		})
	}
	self.get_pings()
}


/* prototypes */

String.prototype.format = String.prototype.f = function() {
	var s = this,
			i = arguments.length;

	while (i--) { s = s.replace(new RegExp('\\{' + i + '\\}', 'gm'), arguments[i]);}
	return s;
};

Array.prototype.alphabetize = function(param) {
	return this.sort(function(a, b) {return a[param] == b[param] ? 0 : (a[param] < b[param] ? -1 : 1) })
}

function seconds_to_time(seconds) {
	function zero_pad(number){
		if (number.toString().length == 1)
			return '0' + number;
		else
			return number;
	}
	var hours = Math.floor(seconds / (60 * 60));

	var divisor_for_minutes = seconds % (60 * 60);
	var minutes = Math.floor(divisor_for_minutes / 60);

	var divisor_for_seconds = divisor_for_minutes % 60;
	var seconds = Math.ceil(divisor_for_seconds);
	
	return '{0}:{1}:{2}'.format(hours, zero_pad(minutes), zero_pad(seconds));
}