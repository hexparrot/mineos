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

function model_property(property, value, section) {
	var self = this;

	self.property = property;
	self.val = ko.observable(value);
	self.section = section;

	var true_false = ['pvp', 'allow-nether', 'spawn-animals', 'enable-query', 
					  'generate-structures', 'hardcore', 'allow-flight', 'online-mode',
					  'spawn-monsters', 'force-gamemode', 'spawn-npcs', 'snooper-enabled',
					  'white-list','enable-rcon'];

	if (true_false.indexOf(property) >= 0) {
		self.type = 'truefalse';
		if (self.val().toLowerCase() == 'true')
			self.val(true);
		else
			self.val(false);
	} else
		self.type = 'textbox';

	self.toggle = function() {
		if (self.val() == true)
			self.val(false)
		else if (self.val() == false)
			self.val(true)
	}
}

function viewmodel() {
	var self = this;

	self.server = ko.observableArray();
	self.page = ko.observableArray();
	self.tasks = ko.observableArray();
	self.tasks_notify = ko.computed(function() {
		return self.tasks().filter(function(i){
		  return i.state == 'error';
		})
	})

	self.dashboard = {
		whoami: ko.observable(),
		memfree: ko.observable(),
		uptime: ko.observable(),
		servers_up: ko.observable()
	}

	self.load_averages = {
		one: [0],
		five: [0],
		fifteen: [0],
		autorefresh: ko.observable(false)
	}

	self.pagedata = {
		pings: ko.observableArray(),
		rdiffs: ko.observableArray(),
		profiles: ko.observableArray(),
		sp: ko.observableArray()
	}

	self.server.extend({ notify: 'always' });
	self.page.extend({ notify: 'always' });

	self.select_server = function(model) {
		self.server(model);
		self.select_page('server_status');
	}

	self.refresh_dashboard = function() {
		$.getJSON('/vm/dashboard')
		.success(function(data){
			self.dashboard.uptime(seconds_to_time(parseInt(data.uptime)));
			self.dashboard.memfree(data.memfree);
			self.dashboard.whoami(data.whoami);
		})

		try {
			self.dashboard.servers_up(vm.pagedata.pings().filter(function(i) {return i.up}).length);
		} catch (e) {
			self.dashboard.servers_up(0)
		}
	}

	self.clear_tasks = function() {
		self.tasks.removeAll();
	}

	self.select_page = function(vm, event) {
		try {
			self.page($(event.currentTarget).data('page'));
		} catch (e) {
			self.page(vm);
		}
	}

	self.page.subscribe(function(page){
		switch(page) {
			case 'dashboard':
				self.refresh_pings();
				self.refresh_dashboard();
				self.redraw_chart();
				break;
			case 'backup_list':
				self.refresh_increments();
				break;	
			case 'server_status':
				self.refresh_pings();
				self.refresh_increments();
				break;
			case 'profiles':
				self.refresh_profiles();
				break;
			case 'create_server':
				self.refresh_profiles();
				break;
			case 'server_properties':
				self.refresh_sp();
				break;
			default:
				break;			
		}

		$('.container-fluid').hide();
		$('#{0}'.format(page)).show();
	})

	self.refresh_pings = function() {
		$.getJSON('/vm/status')
		.success(function(data){
			self.pagedata.pings.removeAll();
			$.each(data.ascending_by('server_name'), function(i,v) {
				self.pagedata.pings.push(new model_status(v));
			})
		})
	}

	self.pagedata.pings.subscribe(function() {
		$.each(self.pagedata.pings(), function(i,v){
			if (self.server().server_name == v.server_name)
				self.server(v);
		})
	})

	self.refresh_increments = function() {
		$.getJSON('/vm/rdiff_backups')
		.success(function(data){
			self.pagedata.rdiffs.removeAll();
			$.each(data, function(i,v) {
				if (v.server_name == self.server().server_name)
					self.pagedata.rdiffs.push(v);
			})
		})
	}

	self.refresh_profiles = function() {
		$.getJSON('/vm/profiles')
		.success(function(data){
			self.pagedata.profiles.removeAll();
			$.each(data, function(i,v) {
				self.pagedata.profiles.push($.extend({profile: i}, v));
			})
		})
	}


	self.define_profile = function(formelement) {
		var step1 = $('form#formwizard2').find('fieldset :input').filter(function() {
		  return ($(this).val() ? true : false);
		})

		var properties = {};
		$.each($(step1).serialize().split('&'), function(i,v) {
		  properties[v.split('=')[0]] = v.split('=')[1]
		})

		var ignored_files = [];
		$('input[name="tags"]').each(function(i,v) {
		  ignored_files.push($(v).val())
		})
		properties.ignore = ignored_files.join(' ')

		delete properties.tags;

		params = {
			'cmd': 'define_profile',
			'profile': JSON.stringify(properties),
		}

		$.getJSON('/host', params)
		.success(function() {
			self.select_page('profiles');
		})

	}

	self.command = function(data, eventobj) {
		var cmd = $(eventobj.currentTarget).data('cmd');
		var required = $(eventobj.currentTarget).data('required').split(',');
		var params = {cmd: cmd};
		var timestamp = (new Date().getTime()) / 1000;
		var id_num = timestamp;

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
				id: id_num,
				timestamp: timestamp,
				state: 'pending',
				command: '{0} {1}'.format(cmd, self.server().server_name)				
			})
			
			$.extend(params, {server_name: self.server().server_name});
			$.getJSON('/server', params)
			.success(function(ret) {

				$.gritter.add({
					title: '{0} {1}: {2}'.format(ret.cmd, ret.server_name, ret.result),
					text: '',
					image: '',
					sticky: false,
					time: '3000',
					class_name: ret.result
				});
				
				$.each(self.tasks(), function(i,v) {
					if (v.id == id_num)  {
						self.tasks.splice(i,1);
					}
				})

				self.tasks.push({
					id: id_num,
					timestamp: timestamp,
					state: ret.result,
					command: '{0} {1}'.format(cmd, self.server().server_name)				
				})

				self.tasks(self.tasks().ascending_by('timestamp').reverse());

				setTimeout(self.page.valueHasMutated, $(eventobj.currentTarget).data('refresh') | 500)
			})
			.fail(function() {
	
			})
		} else {
			var param_text = '';
			$.each(required, function(i,v){
			  param_text += "{0}: {1}<br>".format(v,params[v])
			})

			$.gritter.add({
				title: '{0}'.format(cmd),
				text: param_text,
				image: '',
				sticky: false,
				time: '2000',
				class_name: 'pending'
			});

			$.getJSON('/host', params)
			.success(function(ret) {
				var param_text = '';
				$.each(required, function(i,v){
				  param_text += "{0}: {1}<br>".format(v,params[v])
				})

				$.gritter.add({
					title: '{0}: {1}'.format(ret.cmd, ret.result),
					text: param_text + ret.payload,
					image: '',
					sticky: false,
					time: '3000',
					class_name: ret.result
				});
			})
			.fail(function() {
				
			})
		}
	}

	self.create_server = function(formelement) {
		var server_name = $('form#formwizard1').find('fieldset#step1 input[name=server_name]').val();

		var step1 = $('form#formwizard1').find('fieldset#step1 :input').filter(function() {
		  return ($(this).val() ? true : false);
		})

		var step2 = $('form#formwizard1').find('fieldset#step2 :input').filter(function() {
		  return ($(this).val() ? true : false);
		})

		var step3 = $('form#formwizard1').find('fieldset#step3 :input').filter(function() {
		  return ($(this).val() ? true : false);
		})

		var sp = {};
		$.each($(step2).serialize().split('&'), function(i,v) {
		  sp[v.split('=')[0]] = v.split('=')[1]
		})

		var sc = {};
		$.each(step3, function(i,v) {
		  input = $(v);
		  section = input.data('section');
		  if (!(section in sc))
		    sc[section] = {};
		  sc[section][input.attr('name')] = input.val();
		})

		params = {
			'server_name': server_name,
			'cmd': 'create',
			'sp': JSON.stringify(sp),
			'sc': JSON.stringify(sc)
		}

		$.getJSON('/server', params)
		.success(function() {
			self.select_page('dashboard');
		})

	}

	self.refresh_sp = function() {
		var params = {'server_name': self.server().server_name};
		$.getJSON('/vm/sp', params)
		.success(function(data) {
			self.pagedata.sp.removeAll();
			$.each(data, function(i,v){
				self.pagedata.sp.push(new model_property(i,v));
			})
		})
	}

	self.refresh_loadavg = function(keep_count) {
		$.getJSON('/vm/loadavg')
		.success(function(data){
			self.load_averages.one.push(data[0])
			self.load_averages.five.push(data[1])
			self.load_averages.fifteen.push(data[2])

			while (self.load_averages.one.length > (keep_count + 1)){
				self.load_averages.one.splice(0,1)
				self.load_averages.five.splice(0,1)
				self.load_averages.fifteen.splice(0,1)
			}
		})
	}

	self.redraw_chart = function() {
		var options = {
	        series: { 
	            lines: {
	                show: true,
	                fill: .3
	            },
	            shadowSize: 0 
	        },
	        yaxis: { min: 0, max: 1 },
	        xaxis: { min: 0, max: 30, show: false },
	        grid: {
	            borderWidth: 0, 
	            hoverable: true 
	        }
	    }

        function get_avg(interval) {
            self.refresh_loadavg(options.xaxis.max)
            data = self.load_averages[interval];

            var res = [];
            for (var i = 0; i < data.length; ++i)
                res.push([i, data[i]])
                return res;
        }

        function update() {
        	//colors http://www.jqueryflottutorial.com/tester-4.html

        	if (self.page() != 'dashboard' || !self.load_averages.autorefresh())
        		return

        	var dataset = [
			    { label: "fifteen", data: get_avg('fifteen'), color: "#0077FF" },
			    { label: "five", data: get_avg('five'), color: "#ED7B00" },
			    { label: "one", data: get_avg('one'), color: "#E8E800" }
        	]

        	options.yaxis.max = Math.max(
				self.load_averages.one.max(),
				self.load_averages.five.max(),
				self.load_averages.fifteen.max()) || 1;

        	var plot = $.plot($("#load_averages"), [ get_avg('one') ], options);

            plot.setData(dataset);
            plot.draw();
            setTimeout(update, 1000);
        }   

        update();
	}

	self.toggle_loadaverages = function() {
		if (self.load_averages.autorefresh())
			self.load_averages.autorefresh(false);
		else {
			self.load_averages.autorefresh(true);
			self.redraw_chart();
		}
	}

	self.refresh_dashboard();
	self.select_page('dashboard');
}


/* prototypes */

String.prototype.format = String.prototype.f = function() {
	var s = this,
			i = arguments.length;

	while (i--) { s = s.replace(new RegExp('\\{' + i + '\\}', 'gm'), arguments[i]);}
	return s;
};

Array.prototype.max = function () {
    return Math.max.apply(Math, this);
};

Array.prototype.ascending_by = function(param) {
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