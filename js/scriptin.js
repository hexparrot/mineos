/* webui functions */

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

function viewmodel() {
	var self = this;
	self.pings = ko.observableArray();
	self.whoami = ko.observable();
	self.selected_server = ko.observable('');
	self.selected_server.extend({ notify: 'always' });
	self.current_page = ko.observable();
	self.current_page.extend({ notify: 'always' });
	self.rdiffs = ko.observableArray();
	self.tasks = ko.observableArray();
	
	self.select_server = function(model) {
		self.selected_server(model);	
	}

	self.get_whoami = function() {
		$.get('/whoami')
		.success(function(data){
			self.whoami(data);
		})
	}

	self.get_pings = function() {
		$.getJSON('/vm/status')
		.success(function(data){
			self.pings.removeAll();
			$.each(data, function(i,v) {
				self.pings.push(new model_status(v));
			})
		})
	}

	self.pings.subscribe(function() {
		$.each(self.pings(), function(i,v){
			if (v.server_name == self.selected_server().server_name)
				self.selected_server(v);
		})
	})
	
	self.switch_page = function(vm,event) {
		var page;
		
		try {
			page = $(event.currentTarget).data('page');
		} catch (e) {
			page = vm;
		}

		self.current_page(page);
	}
	
	self.current_page.subscribe(function(page) {
		$('.container-fluid').hide();
		$('#{0}'.format(page)).show();
		
		switch(page) {
			case 'backup_list':
				self.get_increments();
				break;	
			case 'server_status':
				self.get_pings();
				break;
			default:
				break;			
		}
	});
	
	self.get_increments = function() {
		$.getJSON('/vm/rdiff_backups')
		.success(function(data){
			self.rdiffs(data);
		})
	}
	
	self.command = function(data, eventobj) {
		var cmd = $(eventobj.currentTarget).data('cmd');
		var required = $(eventobj.currentTarget).data('required').split(',');
		var params = {cmd: cmd};
		var random_number = Math.floor(Math.random()*100000)
		
		$.each(required, function(i,v) {
			reqd = v.replace(/\s/g, '');
			if (reqd in $(eventobj.currentTarget).data())
				params[reqd] = $(eventobj.currentTarget).data(reqd);
			else if (reqd in data)
				params[reqd] = data[reqd];
		})
		
		if (required.indexOf('force') >= 0) 
			params['force'] = true;

		if (required.indexOf('server_name') >= 0) {
			self.tasks.push({
				id: random_number,
				state: 'pending',
				command: '{0} {1}'.format(cmd, self.selected_server().server_name)				
			})
			
			$.extend(params, {server_name: self.selected_server().server_name});
			$.getJSON('/server', params)
			.success(function(ret) {

				$.gritter.add({
					title: '{0} {1}: {2}'.format(ret.cmd, ret.server_name, ret.result),
					text: '',
					image: '',
					sticky: false,
					time: '3000',
					class_name: (ret.result == 'success' ? 'success' : 'error')
				});
				
				$.each(self.tasks(), function(i,v) {
					if (v.id == random_number)  {
						self.tasks.splice(i,1);
					}
				})
				self.tasks.push({
					id: random_number,
					state: ret.result,
					command: '{0} {1}'.format(cmd, self.selected_server().server_name)				
				})
				self.tasks.reverse();
				
				setTimeout(self.get_pings, 3000);
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

	self.get_pings();
	self.get_whoami();
	self.switch_page('dashboard');
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