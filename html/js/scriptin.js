/* webui functions */

function model_server(data) {
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

function model_property(server_name, option, value, section, new_prop) {
	var self = this;

	self.option = ko.observable(option);
	self.val = ko.observable(value);
	self.section = ko.observable(section);
	self.success = ko.observable(null);
	self.newly_created = ko.observable(new_prop || false);
	self.type = 'textbox';

	self.check_type = function(option, section) {
		if (section) {
			var fixed = [
				{section: 'java', option: 'java_debug', type: 'truefalse'},
				{section: 'onreboot', option: 'restore', type: 'truefalse'},
				{section: 'onreboot', option: 'start', type: 'truefalse'},
				{section: 'crontabs', option: 'archive_interval', type: 'interval'},
				{section: 'crontabs', option: 'backup_interval', type: 'interval'},
				{section: 'crontabs', option: 'restart_interval', type: 'interval'}
			]

			$.each(fixed, function(i,v) {
				if (v.section == section && v.option == option){
					self.type = v.type;
					self.id = v.id;
					return false;
				}
			})
		} else {
			var fixed = [
				{option: 'pvp', type: 'truefalse'},
				{option: 'allow-nether', type: 'truefalse'},
				{option: 'spawn-animals', type: 'truefalse'},
				{option: 'enable-query', type: 'truefalse'},
				{option: 'generate-structures', type: 'truefalse'},
				{option: 'hardcore', type: 'truefalse'},
				{option: 'allow-flight', type: 'truefalse'},
				{option: 'online-mode', type: 'truefalse'},
				{option: 'spawn-monsters', type: 'truefalse'},
				{option: 'force-gamemode', type: 'truefalse'},
				{option: 'spawn-npcs', type: 'truefalse'},
				{option: 'snooper-enabled', type: 'truefalse'},
				{option: 'white-list', type: 'truefalse'},
				{option: 'enable-rcon', type: 'truefalse'},
				{option: 'announce-player-achievements', type: 'truefalse'},
				{option: 'enable-command-block', type: 'truefalse'}
			]

			$.each(fixed, function(i,v) {
				if (v.option == option){
					self.type = v.type;
					return false;
				}
			})
		}

		if (self.type == 'truefalse') {
			if (self.val().toLowerCase() == 'true')
				self.val(true);
			else
				self.val(false);
		}
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

	self.change_select = function(model, eventobj) {
		var new_value = $(eventobj.currentTarget).val();
		var params = {
			server_name: server_name,
			cmd: 'modify_config',
			option: self.option(),
			value: new_value,
			section: self.section()
		}
		$.getJSON('/server', params)
	}

	self.val.subscribe(function(value) {
		function flash_success(data) {
			if (data.result == 'success') {
				self.newly_created(false);
				self.success(true);
				setTimeout(function() {self.success(null)}, 5000)
			} else {
				self.success(false);
			}
		}

		function flash_failure(data) {
			self.success(false);
		}

		var params = {
			server_name: server_name,
			cmd: 'modify_config',
			option: self.option(),
			value: self.val(),
			section: self.section()
		}
		$.getJSON('/server', params).then(flash_success, flash_failure)
	}, self)

	self.check_type(option, section);
	self.id = '{0}_{1}'.format((section ? section : ''), option);
}

function model_logline(str) {
	var self = this;

	self.timestamp = '';
	self.entry = ansi_up.ansi_to_html(ansi_up.linkify(ansi_up.escape_for_html(str)));
}

function model_profile(data) {
	var self = this;
	$.extend(self, data);

	self.description = ko.observable(self.desc);
	self.success = ko.observable(null);

	self.description.subscribe(function(value) {
		var params = {
			cmd: 'modify_profile',
			option: 'desc',
			value: self.description(),
			section: self.profile
		}
		$.getJSON('/host', params)
	}, self)
}

function webui() {
	var self = this;

	self.server = ko.observable({});
	self.page = ko.observable();
	self.profile = ko.observable({});

	self.server.extend({ notify: 'always' });
	self.page.extend({ notify: 'always' });

	self.refresh_rate = 100;
	self.refresh_loadavg = 2000;

	self.dashboard = {
		whoami: ko.observable(''),
		group: ko.observable(),
		groups: ko.observableArray([]),
		memfree: ko.observable(),
		uptime: ko.observable(),
		servers_up: ko.observable(0),
		disk_usage: ko.observable(),
		disk_usage_pct: ko.observable(),
		pc_permissions: ko.observable(),
		pc_group: ko.observable(),
		git_hash: ko.observable(),
		stock_profiles: ko.observableArray([]),
		base_directory: ko.observable()
	}

	self.logs = {
		reversed: ko.observable(true)
	}

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

	self.vmdata = {
		pings: ko.observableArray(),
		archives: ko.observableArray(),
		increments: ko.observableArray(),
		importable: ko.observableArray(),
		profiles: ko.observableArray(),
		sp: ko.observableArray(),
		sc: ko.observableArray(),
		logs: ko.observableArray()
	}

	self.import_information = ko.observable();
	self.profile_type = ko.observable();

	self.summary = {
		backup: {
			most_recent: ko.computed(function() { 
				try { return self.vmdata.increments()[0].timestamp } catch (e) { return 'None' }
			}),
			first: ko.computed(function() {
				try { return self.vmdata.increments()[self.vmdata.increments().length-1].timestamp } catch (e) { return 'None' }
			}),
			cumulative: ko.computed(function() {
				try { return self.vmdata.increments()[self.vmdata.increments().length-1].cumulative_size } catch (e) { return '0 MB' }
			})
		},
		archive: {
			most_recent: ko.computed(function() {
				try { return self.vmdata.archives()[0].friendly_timestamp } catch (e) { return 'None' }
			}),
			first: ko.computed(function() {
				try { return self.vmdata.archives()[self.vmdata.archives().length-1].friendly_timestamp } catch (e) { return 'None' }
			}),
			cumulative: ko.computed(function() {
				return bytes_to_mb(self.vmdata.archives().sum('size'))
			})
		},
		owner: ko.observable(''),
		group: ko.observable(''),
		du_cwd: ko.observable(0),
		du_bwd: ko.observable(0),
		du_awd: ko.observable(0)
	}

	self.pruning = {
		increments: {
			user_input: ko.observable(''),
			remove_count: ko.observable(0),
			step: '',
			space_reclaimed: ko.observable(0.0)
		},
		archives: {
			user_input: ko.observable(),
			filename: ko.observable(),
			remove_count: ko.observable(0),
			archives_to_delete: '',
			space_reclaimed: ko.observable(0.0)
		},
		profiles: {
			profile: ko.observable()
		}
	}

	/* beginning root functions */

	self.toggle_loadaverages = function() {
		if (self.load_averages.autorefresh())
			self.load_averages.autorefresh(false);
		else {
			self.load_averages.autorefresh(true);
			self.redraw.chart();
		}
	}

	self.reset_logs = function() {
		self.vmdata.logs([]);
		$.getJSON('/logs', {server_name: self.server().server_name, reset: true}).then(self.refresh.logs);
	}

	self.select_server = function(model) {
		self.server(model);
		if (self.page() == 'dashboard')
			self.show_page('server_status');
		else
			self.ajax.refresh(null);
	}

	self.select_profile = function(model) {
		self.profile(model);
		self.show_page('profile_view');
	}

	self.new_property = function(vm, event) {
		var config = $(event.target).data('config');

		if (config == 'sp') {
			self.vmdata.sp.push(new model_property(self.server().server_name, null, null, null, true))
		} else if (config == 'sc') {
			self.vmdata.sc.push(new model_property(self.server().server_name, null, null, null, true))
		}
	}

	self.show_page = function(vm, event) {
		try {
			self.page($(event.currentTarget).data('page'));
		} catch (e) {
			self.page(vm);
		}

		$('.container-fluid').hide();
		$('#{0}'.format(self.page())).show();
	}

	self.extract_required = function(required, element, vm) {
		var params = {};
		$.each(required, function(i,v) {
			//checks if required param in DOM element
			//then falls back to vm
			var required_param = v.replace(/\s/g, '');

			if (required_param in $(element).data())
				params[required_param] = $(element).data(required_param);
			else if (required_param in vm)
				params[required_param] = vm[required_param];
		})
		return params;
	}

	self.remember_import = function(model, eventobj) {
		var target = $(eventobj.currentTarget);
		var params = {
			path: model['path'],
			filename: model['filename']
		}

		$.extend(params, self.extract_required(['path','filename'], target, model));

		self.import_information(params);
	}

	self.import_server = function(vm, eventobj) {
		var params = self.import_information();
		params['server_name'] = $('#import_server_modal').find('input[name="newname"]').val();

		$.getJSON('/import_server', params).then(self.ajax.received, self.ajax.lost)
										   .then(self.show_page('dashboard'));
	}

	self.prune_archives = function(vm, eventobj) {
		var params = {
			cmd: 'prune_archives',
			server_name: self.server().server_name,
			filename: self.pruning.archives.archives_to_delete
		}
		$.getJSON('/server', params).then(self.ajax.received, self.ajax.lost)
									.then(function() {self.ajax.refresh(null)});
	}

	self.prune_increments = function(vm, eventobj) {
		var params = {
			cmd: 'prune',
			server_name: self.server().server_name,
			step: self.pruning.increments.step
		}
		$.getJSON('/server', params).then(self.ajax.received, self.ajax.lost)
									.then(function() {self.ajax.refresh(null)});
	}

	self.remember_profile = function(model, eventobj) {
		self.pruning.profiles.profile(model.profile);
	}

	self.prune_profile = function(vm, eventobj) {
		var params = {
			cmd: 'remove_profile',
			profile: self.pruning.profiles.profile
		}
		$.getJSON('/host', params).then(self.ajax.received, self.ajax.lost)
								  .then(function() {self.ajax.refresh(null)});
	}

	self.delete_server = function(vm, eventobj) {
		var params = {
			server_name: self.server().server_name
		}

		var unchecked = $('#delete_confirmations input[type=checkbox]').filter(function(i,v) {
			return !$(v).prop('checked');
		})

		if (unchecked.length == 0) {
			$.getJSON('/delete_server', params)
			.then(self.ajax.received, self.ajax.lost)
			.done(function(){ self.show_page('dashboard') },
				  function(){})
		} else {
			$.gritter.add({
				text: 'No action taken; must confirm all content will be deleted to continue.',
				sticky: false,
				time: '3000',
				class_name: 'gritter-warning'
			});
		}	
	}

	self.change_group = function(vm, eventobj) {
		var params = {
			group: $(eventobj.currentTarget).val(),
			server_name: self.server().server_name
		}

		$.getJSON('/change_group', params).then(self.ajax.received, self.ajax.lost)
	}

	self.change_pc_group = function(vm, eventobj) {
		var params = {
			group: $(eventobj.currentTarget).val()
		}
		$.getJSON('/change_pc_group', params).then(self.ajax.received, self.ajax.lost)
	}

	self.command = function(vm, eventobj) {
		var target = $(eventobj.currentTarget);
		var cmd = $(target).data('cmd');
		var required = $(target).data('required').split(',');
		var params = {cmd: cmd};

		$.extend(params, self.extract_required(required, target, vm));

		if (required.indexOf('force') >= 0)
			params['force'] = true;

		//console.log(params)

		var refresh_time = parseInt($(target).data('refresh'));

		if (required.indexOf('server_name') >= 0) {
			$.extend(params, {server_name: self.server().server_name});
			$.getJSON('/server', params).then(self.ajax.received, self.ajax.lost)
										.then(function() {self.ajax.refresh(refresh_time)});
		} else {
			$.getJSON('/host', params).then(self.ajax.received, self.ajax.lost)
									  .then(function() {self.ajax.refresh(refresh_time)});

		}
	}

	self.page.subscribe(function(page){
		var server_name = self.server().server_name;
		var params = {server_name: server_name};

		switch(page) {
			case 'dashboard':
				$.getJSON('/vm/status').then(self.refresh.pings);
				$.getJSON('/vm/dashboard').then(self.refresh.dashboard).then(self.redraw.gauges);
				self.redraw.chart();
				break;
			case 'backup_list':
				$.getJSON('/vm/increments', params).then(self.refresh.increments);
				break;
			case 'archive_list':
				$.getJSON('/vm/archives', params).then(self.refresh.archives);
				break;	
			case 'server_status':
				$.getJSON('/vm/status').then(self.refresh.pings).then(self.redraw.gauges);
				$.getJSON('/vm/increments', params).then(self.refresh.increments);
				$.getJSON('/vm/archives', params).then(self.refresh.archives);
				$.getJSON('/vm/server_summary', params).then(self.refresh.summary);
				setTimeout(function() {
					$('#delete_server input[type="checkbox"]').not('.nostyle').iCheck({
			            checkboxClass: 'icheckbox_minimal-grey',
			            radioClass: 'iradio_minimal-grey',
			            increaseArea: '40%' // optional
			        });
				}, 500)
				break;
			case 'profiles':
				$.getJSON('/vm/profiles').then(self.refresh.profiles);
				break;
			case 'profile_view':
				$.getJSON('/vm/profiles').then(self.refresh.profiles);
				break;
			case 'create_server':
				$.getJSON('/vm/profiles').then(self.refresh.profiles);
				break;
			case 'server_properties':
				$.getJSON('/server', $.extend({}, params, {'cmd': 'sp'})).then(self.refresh.sp);
				break;
			case 'server_config':
				$.getJSON('/server', $.extend({}, params, {'cmd': 'sc'})).then(self.refresh.sc);
				break;
			case 'importable':
				$.getJSON('/vm/importable', {}).then(self.refresh.importable);
				break;
			case 'console':
				$.getJSON('/logs', params).then(self.refresh.logs);
				break;
			default:
				break;			
		}
	})

	self.pruning.archives.user_input.subscribe(function(new_value) {
		var clone = self.vmdata.archives().slice(0).reverse();
		var match;
		var reclaimed = 0.0;

		$.each(clone, function(i,v) {
			if (v.friendly_timestamp == new_value) {
				match = i;
				self.pruning.archives.filename(v.filename);
				return false;
			}
			reclaimed += v.size;
		})

		if (!match){
			self.pruning.archives.remove_count(0);
			self.pruning.archives.space_reclaimed(0.0);
			self.pruning.archives.archives_to_delete = '';
		} else {
			var hits = clone.slice(0,match).map(function(e) { return e.filename });
			
			self.pruning.archives.remove_count(hits.length);
			self.pruning.archives.space_reclaimed(bytes_to_mb(reclaimed));
			self.pruning.archives.archives_to_delete = hits.join(' ');
		}
	})

	self.pruning.increments.user_input.subscribe(function(new_value){
		var clone = self.vmdata.increments().slice(0).reverse();
		var match;
		var reclaimed = 0.0;

		$.each(clone, function(i,v) {
			if (v.timestamp == new_value || v.step == new_value) {
				match = i;
				self.pruning.increments.step = v.step;
				return false;
			}

			if (v.increment_size.slice(-2) == 'KB')
				reclaimed += parseFloat(v.increment_size) / 1000;
			else
				reclaimed += parseFloat(v.increment_size);
		})

		if (!match){
			self.pruning.increments.remove_count(0);
			self.pruning.increments.space_reclaimed(0);
			self.pruning.increments.step = '';
		} else {
			self.pruning.increments.remove_count(clone.slice(0,match).length);
			self.pruning.increments.space_reclaimed(reclaimed);
		}
	})

	/* form submissions */

	self.create_server = function(form) {
		var server_name = $(form).find('input[name="server_name"]').val();
		var group = $(form).find('select[name=group]').val();

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
		 	sp[v.split('=')[0]] = v.split('=')[1];
		})

		var sc = {};
		$.each(step3, function(i,v) {
			input = $(v);
			section = input.data('section');
			if (!(section in sc))
				sc[section] = {};

			if ($(input).is(':checkbox')) {
				sc[section][input.attr('name')] = $(input).is(':checked');
			} else{
				sc[section][input.attr('name')] = input.val();
			}
			
		})

		params = {
			'server_name': server_name,
			'sp': JSON.stringify(sp),
			'sc': JSON.stringify(sc),
			'group': group
		}

		$.getJSON('/create', params)
		.then(self.ajax.received, self.ajax.lost)
		.done(function() {
			self.show_page('dashboard');
		},function(){

		});
	}

    self.console_command = function(form) {
        var user_input = $(form).find('input[name=console_command]');

        params = {
            cmd: user_input.val(),
            server_name: self.server().server_name
        }

        $.getJSON('/server', params)
        .then(self.ajax.received, self.ajax.lost).then(function() {
            self.ajax.refresh(null);
            user_input.val('');
        });
    }

	self.define_profile = function(form) {
		var step1 = $(form).find('fieldset :input').filter(function() {
			return ($(this).val() ? true : false);
		})

		var properties = {};
		$(step1).each(function() {
		   properties[ $(this).attr('name') ] = $(this).val();
		})

		var props = $(form).find('input[name="tags"]').map(function(i,v) {
			return $(this).val();
		});

		properties['ignore'] = (props.length > 0) ? props.get().join(' ') : '';
		delete properties.tags;

		params = {
			'cmd': 'define_profile',
			'profile_dict': JSON.stringify(properties),
		}

		$.getJSON('/host', params)
		.then(self.ajax.received, self.ajax.lost)
		.done(function() {
			self.show_page('profiles');
		},function(){

		});

	}

	/* promises */

	self.ajax = {
		received: function(data) {
			$.gritter.add({
				text: (data.payload) ? data.payload : '{0} [{1}]'.format(data.cmd, data.result),
				sticky: false,
				time: '3000',
				class_name: 'gritter-{0}'.format(data.result)
			});
			console.log(data);

			if (data.result == 'success')
				return $.Deferred().resolve().promise();
			else
				return $.Deferred().reject().promise();
		},
		lost: function(data) {
			$.gritter.add({
				text: data.payload || 'Server did not respond to request',
				time: '4000',
				class_name: 'gritter-warning'
			});
			console.log(data);

			return $.Deferred().reject().promise();
		},
		refresh: function(time) {
			setTimeout(self.page.valueHasMutated, time || self.refresh_rate)
		}
	}

	self.refresh = {
		dashboard: function(data) {
			self.dashboard.uptime(seconds_to_days(data.uptime));
			self.dashboard.memfree(data.memfree);
			self.dashboard.whoami(data.whoami);
			self.dashboard.group(data.group);
			self.dashboard.disk_usage(data.df);
			self.dashboard.disk_usage_pct((str_to_bytes(self.dashboard.disk_usage().used) / 
										   str_to_bytes(self.dashboard.disk_usage().total) * 100).toFixed(1));
			self.dashboard.groups(data.groups);
			self.dashboard.pc_permissions(data.pc_permissions);
			self.dashboard.pc_group(data.pc_group);
			self.dashboard.git_hash(data.git_hash);
			self.dashboard.stock_profiles(data.stock_profiles);
			self.dashboard.base_directory(data.base_directory);

			$('#pc_group option').filter(function () { 
				return $(this).val() == data.pc_group
			}).prop('selected', true);
		},
		pings: function(data) {
			self.vmdata.pings.removeAll();
			self.dashboard.servers_up(0);
			$.each(data.ascending_by('server_name'), function(i,v) {
				self.vmdata.pings.push( new model_server(v) );

				if (self.server().server_name == v.server_name)
					self.server(new model_server(v));

				if (v.up)
					self.dashboard.servers_up(self.dashboard.servers_up()+1)
			})
		},
		archives: function(data) {
			self.vmdata.archives(data.ascending_by('timestamp').reverse());

			$("input#prune_archive_input").autocomplete({
	            source: self.vmdata.archives().map(function(i) {
				  return i.friendly_timestamp
				})
	        });
		},
		increments: function(data) {
			self.vmdata.increments(data);

			$("input#prune_increment_input").autocomplete({
	            source: self.vmdata.increments().map(function(i) {
				  return i.timestamp
				})
	        });
		},
		summary: function(data) {
			self.summary.owner(data.owner);
			self.summary.group(data.group);
			self.summary.du_cwd(bytes_to_mb(data.du_cwd));
			setTimeout(function() {
				$('#available_groups option').filter(function () { 
					return $(this).val() == self.summary.group()
				}).prop('selected', true)}, 50)
		},
		profiles: function(data) {
			self.vmdata.profiles.removeAll();
			$.each(data, function(i,v) {
				self.vmdata.profiles.push( new model_profile(v) );

				if (self.profile().profile == v.profile)
					self.profile(new model_profile(v));
			})
			self.vmdata.profiles(self.vmdata.profiles().ascending_by('profile'));
		},
		sp: function(data) {
			self.vmdata.sp.removeAll();
			$.each(data.payload, function(option, value) {
				self.vmdata.sp.push( new model_property(self.server().server_name, option, value) )
			})

			self.vmdata.sp(self.vmdata.sp().ascending_by('option'));

			$('table#table_properties input[type="checkbox"]').not('.nostyle').iCheck({
	            checkboxClass: 'icheckbox_minimal-grey',
	            radioClass: 'iradio_minimal-grey',
	            increaseArea: '40%' // optional
	        });
		},
		sc: function(data) {
			self.vmdata.sc.removeAll();
			$.each(data.payload, function(section, option_value_pair){
				$.each(option_value_pair, function(option, value){
					self.vmdata.sc.push(new model_property(self.server().server_name, option, value, section))
				})
			})

			self.vmdata.sc(self.vmdata.sc().ascending_by('section'));

			$('table#table_config input[type="checkbox"]').not('.nostyle').iCheck({
	            checkboxClass: 'icheckbox_minimal-grey',
	            radioClass: 'iradio_minimal-grey',
	            increaseArea: '40%' // optional
	        });

			setTimeout(function() {
		        $.each(self.vmdata.sc(), function(i,v) {
	        		if (v.type == 'interval'){
						$('#{0}_{1} option'.format(v.section(), v.option())).filter(function () { 
							return $(this).val() == v.val()
						}).prop('selected', true)
	        		}
	        	})
			}, 50)
		},
		importable: function(data) {
			self.vmdata.importable(data.ascending_by('filename'));
		},
		logs: function(data) {
			if (!data.payload.length) {
				self.reset_logs();
			} else {
				$.each(data.payload, function(i,v) {
					if (!v.match(/\[INFO\] \/127.0.0.1:\d+ lost connection/) && !v.match(/\[SEVERE\] Reached end of stream for \/127.0.0.1/))
						self.vmdata.logs.push(new model_logline(v));
				})
			}
		}
	}

	/* redraw functions */

	self.judge_severity = function(percent) {
		var colors = ['green', 'yellow', 'orange', 'red'];
		var thresholds = [0, 60, 75, 90];

		var gauge_color = colors[0];
		for (var i=0; i < colors.length; i++) 
			gauge_color = (parseInt(percent) >= thresholds[i] ? colors[i] : gauge_color)

		return gauge_color;
	}

	self.redraw = {
		gauges: function() {
			$('#{0} .gauge'.format(self.page())).easyPieChart({
	            barColor: $color[self.judge_severity( $(this).data('percent') )],
	            scaleColor: false,
	            trackColor: '#999',
	            lineCap: 'butt',
	            lineWidth: 4,
	            size: 50,
	            animate: 1000
	        });
		},
		chart: function() {
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
				setTimeout(update, self.refresh_loadavg);
	        }   
	        update();
		}
	}

	/* viewmodel startup */

	self.show_page('dashboard');
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

Array.prototype.sum = function(param) {
	var total = 0;
	for (var i=0; i < this.length; i++)
		total += this[i][param]
	return total;
}

function seconds_to_days(seconds){
	var numdays = Math.floor(seconds / 86400);
	var numhours = Math.floor((seconds % 86400) / 3600);
	var numminutes = Math.floor(((seconds % 86400) % 3600) / 60);
	var numseconds = ((seconds % 86400) % 3600) % 60;
	return numdays + " days " + ('0' + numhours).slice(-2) + ":" + ('0' + numminutes).slice(-2) + ":" + ('0' + numseconds).slice(-2);
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

function str_to_bytes(str) {
	if (str.substr(-1) == 'G') 
		return parseFloat(str) * Math.pow(10,9);
	else if (str.substr(-1) == 'M') 
		return parseFloat(str) * Math.pow(10,6);
	else if (str.substr(-1) == 'K') 
		return parseFloat(str) * Math.pow(10,3);
	else
		return parseFloat(str);
}

function bytes_to_mb(bytes){
	//http://stackoverflow.com/a/15901418/1191579
    if ( ( bytes >> 30 ) & 0x3FF )
        bytes = ( bytes >>> 30 ) + '.' + (bytes & (3*0x3FF )).toString().substring(0,2) + 'GB';
    else if ( ( bytes >> 20 ) & 0x3FF )
        bytes = ( bytes >>> 20 ) + '.' + (bytes & (2*0x3FF )).toString().substring(0,2) + 'MB';
    else if ( ( bytes >> 10 ) & 0x3FF )
        bytes = ( bytes >>> 10 ) + '.' + (bytes & (0x3FF )).toString().substring(0,2) + 'KB';
    else if ( ( bytes >> 1 ) & 0x3FF )
        bytes = ( bytes >>> 1 ) + ' b' ;
    else
        bytes = bytes + ' b' ;
    return bytes;
}
