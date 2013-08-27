/* webui functions */

function model_status(data) {
	var self = this;
	$.extend(self, data);
	
	self.mem_utilization = ko.computed(function() {
		return '{0} / {1}'.format(parseInt(self.memory), self.java_xmx);
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

	self.online_pct = ko.computed(function() {
		return parseInt((self.players_online / self.max_players) * 100)
	})

	self.memory_pct = ko.computed(function() {
		return parseInt((parseInt(self.memory) / parseInt(self.java_xmx)) * 100)
	})
}

function model_property(server_name, option, value, section) {
	var self = this;

	self.option = option;
	self.val = ko.observable(value);
	self.section = section;
	self.success = ko.observable(null);

	if (section) {
		var true_false = [
			['onreboot', 'restore'],
			['onreboot', 'start']
		];

		var match = true_false.filter(function(v) {
		  return self.section == v[0] && self.option == v[1]
		})

		if (match.length) {
			self.type = 'truefalse';
			if (self.val().toLowerCase() == 'true')
				self.val(true);
			else
				self.val(false);
		} else {
			self.type = 'textbox';
		}
	} else {
		var true_false = ['pvp', 'allow-nether', 'spawn-animals', 'enable-query', 
						  'generate-structures', 'hardcore', 'allow-flight', 'online-mode',
						  'spawn-monsters', 'force-gamemode', 'spawn-npcs', 'snooper-enabled',
						  'white-list','enable-rcon'];

		if (true_false.indexOf(option) >= 0) {
			self.type = 'truefalse';
			if (self.val().toLowerCase() == 'true')
				self.val(true);
			else
				self.val(false);
		} else
			self.type = 'textbox';
	}

	self.toggle = function(model, eventobj) {
		$(eventobj.currentTarget).find('input').iCheck('destroy');

		if (self.val() == true) {
			$(eventobj.currentTarget).find('input').iCheck('uncheck');
			self.val(false);
		} else if (self.val() == false) {
			var target = $(eventobj.currentTarget).find('input');
			$(target).iCheck({
	            checkboxClass: 'icheckbox_minimal-grey',
	            radioClass: 'iradio_minimal-grey',
	            increaseArea: '40%' // optional
	        });
			$(target).iCheck('check');
			self.val(true);
		}
	}

	self.val.subscribe(function(value) {
		var params = {
			server_name: server_name,
			cmd: 'modify_config',
			option: self.option,
			value: self.val(),
			section: self.section
		}
		$.getJSON('/server', params)
		.success(function(data) {
			if (data.result == 'success') {
				self.success(true);
				setTimeout(function() {
					self.success(null);
				}, 5000)
			} else {
				self.success(false);
			}
		})

	}, self)
}

function model_increment(enumeration, inc_data) {
	var self = this;
	self.step = '{0}B'.format(enumeration);

	self.timestamp = inc_data[0];
	self.increment_size = inc_data[1];
	self.cumulative_size = inc_data[2];
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
		servers_up: ko.observable(),
		df: ko.observable(),
		confirm_removal: ko.observable()
	}

	self.dashboard['df_pct'] = ko.computed(function() {
		function expand(size) {
			if (size.substr(-1) == 'G')
				return parseFloat(size) * 1000;
			else if (size.substr(-1) == 'M')
				return parseFloat(size)
			else if (size.substr(-1) == 'K')
				return parseFloat(size) / 1000.0; 
		}

		try {
			return Math.round(expand(self.dashboard.df().used) / expand(self.dashboard.df().total) * 100);
		} catch (e) {
			return '--';
		}
	})

	self.load_averages = {
		one: [0],
		five: [0],
		fifteen: [0],
		autorefresh: ko.observable(true),
		options: {
	        series: { 
	            lines: {
	                show: true,
	                fill: .3
	            },
	            shadowSize: 0 
	        },
	        yaxis: { 
	        	min: 0, 
	        	max: 1,
	        	axisLabel: "Load Average for last minute",
		        axisLabelUseCanvas: true,
		        axisLabelFontSizePixels: 12,
		        axisLabelFontFamily: 'Verdana, Arial',
		        axisLabelPadding: 3
	        },
	        xaxis: { min: 0, max: 30, show: false },
	        grid: {
	            borderWidth: 0, 
	            hoverable: false 
	        },
	        legend: {
		        labelBoxBorderColor: "#858585",
		        position: "ne"
		    }
	    }
	}

	self.pagedata = {
		pings: ko.observableArray(),
		archives: ko.observableArray(),
		rdiffs: ko.observableArray(),
		profiles: ko.observableArray(),
		sp: ko.observableArray(),
		sc: ko.observableArray()
	}

	self.backup_summary = {
		last_backup: ko.computed(function() {
			try {
				return self.pagedata.rdiffs()[0].timestamp;
			} catch (e) {
				return 'None';
			}
		}),
		cumulative_size: ko.computed(function() {
			try {
				return self.pagedata.rdiffs()[0].cumulative_size;
			} catch (e) {
				return '0 MB';
			}
		}),
		frequency: ko.computed(function() {
			try {
				return self.pagedata.rdiffs()[0].cumulative_size;
			} catch (e) {
				return '0 MB';
			}
		}),
		first_backup: ko.computed(function() {
			try {
				return self.pagedata.rdiffs()[self.pagedata.rdiffs().length-1].timestamp;
			} catch (e) {
				return 'None';
			}
		})
	}

	self.archive_summary = {
		last_archive: ko.computed(function() {
			try {
				return self.pagedata.archives()[0].friendly_timestamp;
			} catch (e) {
				return 'None';
			}
		}),
		cumulative_size: ko.computed(function() {
			var cumulative = 0;
			$.each(self.pagedata.archives(), function(i,v) {
				cumulative += v.size
			})
			return bytes_to_mb(cumulative);
		}),
		first_archive: ko.computed(function() {
			try {
				return self.pagedata.archives()[self.pagedata.archives().length-1].friendly_timestamp;
			} catch (e) {
				return 'None';
			}
		})
	}

	self.prune = {
		user_input: ko.observable(),
		steps: ko.observable(),
		to_remove: ko.observable(0),
		space_reclaimed: ko.observable(0.0)
	}

	self.archive = {
		user_input: ko.observable(),
		filename: ko.observable(),
		archives_to_delete: ko.observableArray(),
		to_remove: ko.observable(0),
		space_reclaimed: ko.observable(0.0)
	}

	self.server.extend({ notify: 'always' });
	self.page.extend({ notify: 'always' });

	self.select_server = function(model) {
		self.server(model);
		self.select_page('server_status');
	}

	self.refresh_dashboard = function(data) {
		self.dashboard.uptime(seconds_to_time(parseInt(data.uptime)));
		self.dashboard.memfree(data.memfree);
		self.dashboard.whoami(data.whoami);
		self.dashboard.df(data.df);

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
		var server_name = self.server().server_name;
		var params = {server_name: server_name};

		switch(page) {
			case 'dashboard':
				$.getJSON('/vm/status').then(self.refresh_pings);
				$.getJSON('/vm/dashboard').then(self.refresh_dashboard).then(self.redraw_gauges);
				self.redraw_chart();
				break;
			case 'backup_list':
				$.getJSON('/vm/increments', params).then(self.refresh_increments);
				break;
			case 'archive_list':
				$.getJSON('/vm/archives', params).then(self.refresh_archives);
				break;	
			case 'server_status':
				$.getJSON('/vm/status').then(self.refresh_pings).then(self.redraw_gauges);
				$.getJSON('/vm/increments', params).then(self.refresh_increments);
				$.getJSON('/vm/archives', params).then(self.refresh_archives);
				break;
			case 'profiles':
				$.getJSON('/vm/profiles').then(self.refresh_profiles);
				break;
			case 'create_server':
				$.getJSON('/vm/profiles').then(self.refresh_profiles);
				break;
			case 'server_properties':
				$.getJSON('/server', $.extend({}, params, {'cmd': 'sp'})).then(self.refresh_sp);
				break;
			case 'server_config':
				$.getJSON('/server', $.extend({}, params, {'cmd': 'sc'})).then(self.refresh_sc);
				break;
			default:
				break;			
		}

		$('.container-fluid').hide();
		$('#{0}'.format(page)).show();

	})

	self.refresh_pings = function(data) {
		self.pagedata.pings.removeAll();
		$.each(data.ascending_by('server_name'), function(i,v) {
			self.pagedata.pings.push(new model_status(v));
		})
	}

	self.pagedata.pings.subscribe(function() {
		$.each(self.pagedata.pings(), function(i,v){
			if (self.server().server_name == v.server_name)
				self.server(v);
		})
	})

	self.archive.user_input.subscribe(function(new_value) {
		var clone = self.pagedata.archives().slice(0).reverse();
		var match;
		var reclaimed = 0.0;

		$.each(clone, function(i,v) {
			if (v.friendly_timestamp == new_value) {
				match = i;
				self.archive.filename(v.filename);
				return false;
			}
			reclaimed += v.size;
		})

		if (!match){
			self.archive.archives_to_delete('');
			self.archive.to_remove(0);
			self.archive.space_reclaimed(0.0);
		} else {
			self.archive.archives_to_delete(clone.slice(0,match).map(function(e) {
			  return e.filename;
			}).join(' '))
			self.archive.to_remove(clone.slice(0,match).length);
			self.archive.space_reclaimed(bytes_to_mb(reclaimed));
			$('#go_prune2').data('filename', self.archive.archives_to_delete())
		}
	})

	self.refresh_archives = function(data) {
		self.pagedata.archives(data.ascending_by('timestamp').reverse());

		var available_tags = vm.pagedata.archives().map(function(i) {
		  return i.friendly_timestamp
		})

		$("#prune_archives").autocomplete({
            source: available_tags
        });
	}

	self.prune.user_input.subscribe(function(new_value) {
		var clone = self.pagedata.rdiffs().slice(0).reverse();
		var match;
		var reclaimed = 0.0;

		$.each(clone, function(i,v) {
			if (v.timestamp == new_value || v.step == new_value) {
				match = i;
				self.prune.steps(v.step);
				return false;
			}

			if (v.increment_size.slice(-2) == 'KB')
				reclaimed += parseFloat(v.increment_size) / 1000;
			else
				reclaimed += parseFloat(v.increment_size);
		})

		if (!match){
			self.prune.to_remove(0);
			self.prune.space_reclaimed(0);
		} else {
			self.prune.to_remove(clone.slice(0,match).length);
			self.prune.space_reclaimed(reclaimed);
			$('#go_prune').data('steps', self.prune.steps())
		}
	})

	self.refresh_increments = function(data) {
		self.pagedata.rdiffs(data)

		var available_tags = vm.pagedata.rdiffs().map(function(i) {
		  return i.timestamp
		})

		$("#prune_intervals").autocomplete({
            source: available_tags
        });
	}

	self.removal_confirmation = function(vm, event) {
		try {
			$('#confirm_removal').data('profile', vm.profile);
		} catch (e) {
			$('#confirm_removal').data('profile', '');
		}

		self.dashboard.confirm_removal($('#confirm_removal').data('profile'))
	}

	self.refresh_profiles = function(data) {
		self.pagedata.profiles.removeAll();
		$.each(data, function(i,v) {
			self.pagedata.profiles.push($.extend({profile: i}, v));
		})
		self.pagedata.profiles(self.pagedata.profiles().ascending_by('profile'))
	}

	self.define_profile = function(formelement) {
		var form = $('form#definenewprofile');
		var step1 = $(form).find('fieldset :input').filter(function() {
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

		function pending_gritter(required) {
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
		}

		function success_gritter(required, ret) {
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
		}

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
			pending_gritter(required);

			$.getJSON('/server', params)
			.success(function(ret) {

				success_gritter(required, ret)
				
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

				if (ret.result != 'success')
					console.log(ret)

				self.tasks(self.tasks().ascending_by('timestamp').reverse());
				setTimeout(self.page.valueHasMutated, parseInt($(eventobj.currentTarget).data('refresh')) || 50)
			})
		} else {
			pending_gritter(required)

			$.getJSON('/host', params)
			.success(function(ret) {
				success_gritter(required, ret)

				if (ret.result != 'success')
					console.log(ret)

				setTimeout(self.page.valueHasMutated, parseInt($(eventobj.currentTarget).data('refresh')) || 50)
			})
		}
	}

	self.create_server = function(formelement) {
		var form = $('form#createnewserver');
		var server_name = $(form).find('fieldset#step1 input[name=server_name]').val();

		var step1 = $(form).find('fieldset#step1 :input').filter(function() {
		  return ($(this).val() ? true : false);
		})

		var step2 = $(form).find('fieldset#step2 :input').filter(function() {
		  return ($(this).val() ? true : false);
		})

		var step3 = $(form).find('fieldset#step3 :input').filter(function() {
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

	self.refresh_sp = function(data) {
		self.pagedata.sp.removeAll();
		$.each(data.payload, function(i,v){
			self.pagedata.sp.push(new model_property(self.server().server_name, i,v));
		})

		$('#table_properties input[type="checkbox"]').not('.nostyle').iCheck({
            checkboxClass: 'icheckbox_minimal-grey',
            radioClass: 'iradio_minimal-grey',
            increaseArea: '40%' // optional
        });
	}

	self.refresh_sc = function(data) {
		self.pagedata.sc.removeAll();
		$.each(data.payload, function(i,v){
			$.each(v, function(a,b){
				self.pagedata.sc.push(new model_property(self.server().server_name,a,b,i));
			})
		})

		$('#table_config input[type="checkbox"]').not('.nostyle').iCheck({
            checkboxClass: 'icheckbox_minimal-grey',
            radioClass: 'iradio_minimal-grey',
            increaseArea: '40%' // optional
        });
	}

	self.redraw_gauges = function() {
		function judge_color(percent, colors, thresholds) {
			var gauge_color = colors[0];
			for (var i=0; i < colors.length; i++) {
				gauge_color = (parseInt(percent) >= thresholds[i] ? colors[i] : gauge_color)
			}
			return gauge_color;
		}

		var colors = ['green', 'yellow', 'orange', 'red'];
		var thresholds = [0, 60, 75, 90];

		$('#{0} .gauge'.format(vm.page())).easyPieChart({
            barColor: $color[judge_color($(this).data('percent'), colors, thresholds)],
            scaleColor: false,
            trackColor: '#999',
            lineCap: 'butt',
            lineWidth: 4,
            size: 50,
            animate: 1000
        });
	}

	self.redraw_chart = function() {

		function rerender(data) {
			function enumerate(arr) {
	            var res = [];
	            for (var i = 0; i < arr.length; ++i)
	                res.push([i, arr[i]])
	                return res;
	        }

	        self.load_averages.one.push(data[0])
			self.load_averages.five.push(data[1])
			self.load_averages.fifteen.push(data[2])

			while (self.load_averages.one.length > (self.load_averages.options.xaxis.max + 1)){
				self.load_averages.one.splice(0,1)
				self.load_averages.five.splice(0,1)
				self.load_averages.fifteen.splice(0,1)
			}

			//colors http://www.jqueryflottutorial.com/tester-4.html
	        var dataset = [
			    { label: "fifteen", data: enumerate(self.load_averages['fifteen']), color: "#0077FF" },
			    { label: "five", data: enumerate(self.load_averages['five']), color: "#ED7B00" },
			    { label: "one", data: enumerate(self.load_averages['one']), color: "#E8E800" }
        	]

        	self.load_averages.options.yaxis.max = Math.max(
				self.load_averages.one.max(),
				self.load_averages.five.max(),
				self.load_averages.fifteen.max()) || 1;

        	var plot = $.plot($("#load_averages"), dataset, self.load_averages.options);
            plot.draw();
		}

        function update() {
        	if (self.page() != 'dashboard' || !self.load_averages.autorefresh()) {
				self.load_averages.one.push.apply(self.load_averages.one, [0,0,0])
				self.load_averages.five.push.apply(self.load_averages.five, [0,0,0])
				self.load_averages.fifteen.push.apply(self.load_averages.fifteen, [0,0,0])
        		return
        	}

        	$.getJSON('/vm/loadavg').then(rerender);
			setTimeout(update, 2000);
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

function bytes_to_mb(bytes){
	//http://stackoverflow.com/a/15901418/1191579
    if ( ( bytes >> 30 ) & 0x3FF )
        bytes = ( bytes >>> 30 ) + '.' + (bytes & (3*0x3FF )).toString().substring(0,2) + 'GB' ;
    else if ( ( bytes >> 20 ) & 0x3FF )
        bytes = ( bytes >>> 20 ) + '.' + (bytes & (2*0x3FF )).toString().substring(0,2) + 'MB' ;
    else if ( ( bytes >> 10 ) & 0x3FF )
        bytes = ( bytes >>> 10 ) + '.' + (bytes & (0x3FF )).toString().substring(0,2) + 'KB' ;
    else if ( ( bytes >> 1 ) & 0x3FF )
        bytes = ( bytes >>> 1 ) + 'Bytes' ;
    else
        bytes = bytes + 'Byte' ;
    return bytes;
}