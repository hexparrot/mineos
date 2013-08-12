// JavaScript Document

var server_url = 'cgi-bin/server.py';
var filter_spam = [
		/127\.0\.0\.1:[^\s]+ lost connection/,
		/Reached end of stream/
	];

/* models */

function model_profile(p) {
	var self = this;
	$.extend(self, p);
	self.downloading = ko.observable(false);

	self.is_found = ko.computed(function() {
		return self.timestamp != 'not-found';
	});
	
	self.is_runnable = ko.computed(function() {
		return self.download_type == 'script';
	});
	
	self.executable = ko.computed(function() {
		return (self.download_type == 'script' ? self.script_filename : self.jar_filename);
	});
	
	self.container = ko.computed(function() {
		return (self.archive_filename ? self.archive_filename : '')
	});
	
	self.download_profile = function() {
		if (!self.downloading()) {
			self.downloading(true);
			var param = {server_name: '', 'function': 'update_profile', profile: self.profile};
			$.getJSON(server_url, param, function(data) {
				self.downloading(false);
				if (data.success) {
					toaster(data.success, '{0}'.format(data.function), 'Successfully updated {0} profile'.format(self.profile));
					refresh_page(500);
				} else
					toaster(data.success, '{0}'.format(data.function), data.message );
			});	
		}		
	}
	
	self.execute_profile = function() {
		if (!self.downloading()) {
			self.downloading(true);
			var param = {server_name: '', 'function': 'execute_profile', profile: self.profile};
			$.getJSON(server_url, param, function(data) {
				self.downloading(false);
				if (data.success)
					toaster(data.success, '{0}'.format(data.function), 'Successfully ran script: {0}'.format(self.script_filename));
				else
					toaster(data.success, '{0}'.format(data.function), data.message );
			});
		}
	}
}

function model_script(p) {
	var self = this;
	$.extend(self, p);
	
	self.is_beta = ko.computed(function() {
		return self.beta == self.version;
	});

	self.is_stable = ko.computed(function() {
		return self.stable == self.version;
	});
}

function model_server(p) {
	var self = this;
	$.extend(self, p);
	self.working = ko.observable(false);
	
	self.status = ko.computed(function() {
		return (self.ping.players < 0 ? 'DENY' : (self.up ? 'up' : 'down'));
	})
	
	self.players_online = ko.computed(function() {
		try {
			if (self.ping.max_players)
				return "{0} / {1}".format(self.ping.players || 0, self.ping.max_players);
		} catch (err) {
			return ' / ';
		}
	})
	
	self.memory_usage = ko.computed(function() {
		try {
			return "{0} / {1}".format((self.mem_usage ? parseInt(self.mem_usage/1000) : 0),
																(self.mem_allotted ? self.mem_allotted : ''));
		} catch (err) {
			return ' / ';
		}
	})
	
	self.overextended = ko.computed(function() {
		try {
			return (parseInt(self.mem_usage/1000) > self.mem_allotted ? true : false);
		} catch (err) {
			return false;
		}
	})
	
	self.start = function() {
		if (!self.working()) {
			self.working(true);
			var param = {server_name: self.server_name, 'function': 'start'};
			$.getJSON(server_url, param, function(data) {
				self.working(false);
				if (data.success) {
					toaster(!!data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Successfully started server');
					refresh_page(5000);
				} else
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);				
			});
		}
	}

	self.stop = function() {
		if (!self.working()) {
			self.working(true);
			var param = {server_name: self.server_name, 'function': 'stop'};
			$.getJSON(server_url, param, function(data) {
				self.working(false);
				if (data.success) {
					toaster(!!data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Successfully stopped server');
					refresh_page(5000);
				} else
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);				
			});
		}
	}

	self.kill = function() {
		if (!self.working()) {
			self.working(true);
			var param = {server_name: self.server_name, 'function': 'kill'};
			$.getJSON(server_url, param, function(data) {
				self.working(false);
				if (data.success) {
					toaster(!!data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Successfully terminated server by PID');
					refresh_page(2000);
				} else
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);				
			});
		}
	}	
}

function model_backup(p) {
	var self = this;
	$.extend(self, p);
	self.working = ko.observable(false);
	
	self.status = ko.computed(function() {
		return (self.up ? 'up' : 'down');
	})
	
	self.backup_status = ko.computed(function() {
		return (self.snapshots > 0 ? 'found' : '')
	})
	
	self.backup = function() {
		if (!self.working()) {
			self.working(true);
			var param = {server_name: self.server_name, 'function': 'backup'};
			$.getJSON(server_url, param, function(data) {
				self.working(false);
				if (data.success) {
					toaster(!!data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Successfully backed up server');
					refresh_page(500);
				} else
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);	
			});
		}
	}

	self.archive = function() {
		if (!self.working()) {
			self.working(true);
			var param = {server_name: self.server_name, 'function': 'archive'};
			$.getJSON(server_url, param, function(data) {
				self.working(false);
				if (data.success)
					toaster(!!data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Successfully archived server');
				else
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);	
			});
		}
	}	
	
	self.show_increment_table = function(model, event) {
		show_page({dest: '#increments', server_name: model.server_name, nofade: true});
	}
	
	self.show_prune_table = function(model, event) {
		show_page({dest: '#pruning', server_name: model.server_name, nofade: true});
	}
}

function model_increment(server_name, order, string) {
	var self = this;
	self.server_name = server_name;
	self.string = string;
	self.working = ko.observable(false);
	
	self.segments = self.string.split(/[\s]{3,}/);
	self.steps = "{0}B".format(order);

	self.is_increment = ko.computed(function() {
		if (self.segments[0] != 'Time' && self.segments.length >= 3)
			return true;
		return false;
	});	
	
	self.restore = function() {
		if (!self.working()) {
			self.working(true);
			var param = {server_name: self.server_name, 'function': 'restore', steps: self.steps, overwrite: true};
			$.getJSON(server_url, param, function(data) {
				self.working(false);
				if (data.success) 
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Successfully applied restore point ' + self.steps);
				else
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);		
			});
		}		
	}
	
	self.prune = function() {
		if (!self.working()) {
			self.working(true);
			var param = {server_name: self.server_name, 'function': 'prune', steps: self.steps};
			$.getJSON(server_url, param, function(data) {
				self.working(false);
				if (data.success) 
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Successfully pruned restore points older than ' + self.steps);
				else
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);	
			});
		}
	}
}

function model_attribute(server_name, triplet, state) {
	var self = this;
	self.state = ko.observable(state || 'saved');  // 'new', 'editing', 'saved'
	
	self.server_name = server_name;
	self.section = triplet.section;
	self.key = triplet.key;
	self.value = triplet.value;
	
	self.edit = function() {
		if (self.state() == 'new')
			return;
		self.state('editing');
	}
	
	self.save = function() {
		if (!self.section.length || !self.key.length)
			return;
		
		var param = {server_name: self.server_name};
		
		if (this.section == 'sectionless') {
			param['function'] = 'change_sp';
			param[self.key] = self.value;
		} else {
			param['function'] = 'change_sc';
			param['key'] = self.key;
			param['value'] = self.value;	
			param['section'] = self.section;
		}

		$.getJSON(server_url, param, function(data) {
			self.state('saved');
			if (!data.success) 
				toaster('warning', '[{0}] {1}'.format(param.server_name, param.function), data.message );				
		});
	}
}

function model_log_entry(p) {
	var self = this;
	self.types = {
		0: 'INFO',
		1: 'WARNING',
		2: 'SEVERE',
		3: 'FINE',
		4: 'FINER',
		5: 'FINEST'
	}	
	
	if (typeof p == 'string') {
		var matches = p.match(/(.+?) \[(.+?)\] (.*)/);
	
		if (matches) {
			self.timestamp = matches[1];
			self.type = matches[2];
			self.entry = matches[3];
		} else {
			self.timestamp = '';
			self.type = '';
			self.entry = p;
		}
	} else if (typeof p == 'object') {
		self.timestamp = new Date(p.timestamp*1000).toString().substr(0,24);
		self.type = self.types[p.type];
		self.entry = p.data;		
	} else {
		self.timestamp = null;
		self.type = null;
		self.entry = null;
	}
	
	self.matches = function(arr) {
		for (var idx in arr) {
			if (self.entry.match(arr[idx]))
				return true;
		}
		return false;
	};
}

/* viewmodels */

function viewmodel_navigation() {
	var self = this;
	self.navigation = ko.observableArray([
		{caption: 'Overview', dest: '#overview'},
		{caption: 'Server Status', dest: '#server_status'},
		{caption: 'Backup and Restore', dest: '#backup_restore'},
		{caption: 'Create New Server', dest: '#create_server'},
		{caption: 'Modify Config', dest: '#modify_config'},
		{caption: 'Server Console', dest: '#server_console'},
		{caption: 'System Health', dest: '#system_health'}
	]);
}

function viewmodel_profiles() {
	var self = this;
	self.profiles = ko.observableArray();
	
	self.refresh = function() {
		var param = {server_name: '', 'function': 'vm_profile'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) {
				self.profiles.removeAll();
				$.each(data.payload.alphabetize('profile'), function() {
					self.profiles.push(new model_profile(this));
				});
			}
		});
	}
	
	self.show_create_profile = function() {
		show_page({dest: '#create_profile', nofade: true});
	}
	
}

function viewmodel_profiles_create() {
	var self = this;
	
	self.profile = ko.observable('');
	self.selected_type = ko.observable();
	self.url = ko.observable('');
	self.url_savename = ko.observable('');
	self.update = false;
	self.server_jar = ko.observable('');
	self.command_args = ko.observable('');
	self.ignore_files = ko.observable('');
	
	self.profile_types = [
		{caption: 'Server file enclosed in a .JAR', value: 0},
		{caption: 'Server file enclosed in a .ZIP', value: 1},
		{caption: 'Server file enclosed in a .TGZ', value: 2},
		{caption: 'Runnable shell script - .sh', value: 3},
		{caption: 'Generic archive file - .tgz', value: 4},
		{caption: 'Generic archive file - .zip', value: 5}
	];
	
	self.is_container = ko.computed(function() {
		if ([1,2,4,5].indexOf(self.selected_type()) >= 0)
			return true;		
	})
	
	self.is_serverjar = ko.computed(function() {
		if ([0,1,2].indexOf(self.selected_type()) >= 0)
			return true;		
	})
	
	self.create_new_profile = function() {
		var download_type = {
			0: 'jar',
			1: 'zip',
			2: 'tgz',
			3: 'sh',
			4: 'tgz',
			5: 'zip'		
		};

		var param = {
			server_name: '',
			function: 'create_profile',
			profile: self.profile(),
			update: (self.update ? true : false),
			url: self.url(),
			ignore: self.ignore_files(),
			download_type: download_type[self.selected_type()]
		};
		
		if (self.is_serverjar()) {
			param.jar_file = self.server_jar();
			param.jar_args = self.command_args();
		}
		
		if (self.is_container()) {
			param[download_type[self.selected_type()] + '_file'] = self.url_savename();
		}
		
		$.getJSON(server_url, param, function(data) {
			if (data.success)
				toaster(data.success, '{0}'.format(param.function), 'Created new profile: {0}'.format(self.profile()));
			else
				toaster(data.success, '{0}'.format(param.function), data.message);
		});
	}
}

function viewmodel_scripts() {
	var self = this;
	self.scripts = ko.observableArray();
	self.updating = ko.observable(false);
	
	self.refresh = function() {
		var param = {server_name: '', 'function': 'vm_version'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) {
				self.scripts.removeAll();
				$.each(data.payload.alphabetize('file'), function() {
					self.scripts.push(new model_script(this));
				});
			}				
		});
	}

	self.update_versions = function() {
		if (!self.updating()) {
			self.updating(true);
			var param = {server_name: '', 'function': 'update_versions'};
			$.getJSON(server_url, param, function(data) {
				self.updating(false);
				if (data.success) {
					toaster(data.success, data.function, 'Updating table with latest versions of scripts....');
					self.refresh();
				} else
					toaster(data.success, data.function, data.message);
			});			
		}
	}
	
	self.update_stable = function() {
		if (!self.updating()) {
			self.updating(true);
			var param = {server_name: '', 'function': 'update_stable'};
			$.getJSON(server_url, param, function(data) {
				self.updating(false);
				if (data.success) {
					toaster(data.success, data.function, 'Stable script channel updated and activated. Be sure to refresh this page/clear cache in your browser.');
					self.refresh();
				} else
					toaster(data.success, data.function, data.message);
			});			
		}
	}

	self.update_beta = function() {
		if (!self.updating()) {
			self.updating(true);
			var param = {server_name: '', 'function': 'update_beta'};
			$.getJSON(server_url, param, function(data) {
				self.updating(false);
				if (data.success) {
					toaster(data.success, data.function, 'Beta script channel updated and activated. Be sure to refresh this page/clear cache in your browser.');
					self.refresh();
				} else
					toaster(data.success, data.function, data.message);
			});			
		}
	}	
}

function viewmodel_servers() {
	var self = this;
	self.servers = ko.observableArray();
	
	self.refresh = function() {
		var param = {server_name: '', 'function': 'vm_server'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) {
				self.servers.removeAll();
				$.each(data.payload.alphabetize('server_name'), function() {
					self.servers.push(new model_server(this));
				});
			}
		});
	}
}

function viewmodel_backups() {
	var self = this;
	
	self.backups = ko.observableArray();
	self.restores = ko.observableArray();
	
	self.refresh = function() {
		var param = {server_name: '', 'function': 'vm_backup'};
		$.getJSON(server_url, param, function(data) {
			self.backups.removeAll();
			self.restores.removeAll();
			$.each(data.payload.alphabetize('server_name'), function(i,v) {
				self.backups.push(new model_backup(v));
				if (v.snapshots > 0) {
					self.restores.push(new model_backup(v));
				}
			});
		});	
	}
}

function viewmodel_increments() {
	var self = this;
	self.increments = ko.observableArray();
	
	self.refresh = function(server_name) {
		var param = {'server_name': server_name, 'function': 'list_restore_points_size'};
		$.getJSON(server_url, param, function(data) {
			self.increments.removeAll();
			var counter = 0;
			$.each(data.payload, function(i,v) {
				var temp = new model_increment(server_name, counter, v);
				if (temp.is_increment()) {
					self.increments.push(temp);
					counter++;
				}
			});
		});
	}
}

function viewmodel_create() {
	var self = this;
	self.profiles = ko.observableArray();
	self.importables = ko.observableArray();
	self.selected_archive = ko.observable();
	
	self.frequency = ko.observableArray(['none', 'hourly', 'daily', 'weekly']);
	self.difficulty = ko.observableArray([
		{ caption: 'Peaceful', value: 0 },
		{ caption: 'Easy', value: 1 },
		{ caption: 'Normal', value: 2 },
		{ caption: 'Hard', value: 3 }
	]);
		
	self.gamemode = ko.observableArray([
		{ caption: 'Survival', value: 0 },
		{ caption: 'Creative', value: 1 },
		{ caption: 'Adventure', value: 2 }
	]);

	self.level_type = ko.observableArray([
		{ caption: 'DEFAULT', value: 'DEFAULT' },
		{ caption: 'FLAT', value: 'FLAT' },
		{ caption: 'LARGEBIOMES', value: 'LARGEBIOMES' }
	]);	
	
	self.populate_profiles = function() {
		var param = {server_name: '', 'function': 'list_usable_profiles'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) {
				self.profiles( data.payload.alphabetize('profile') );
			}
		});		
	}
	
	self.populate_importables = function() {
		var param = {server_name: '', 'function': 'list_importable_archives'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) 
				self.importables( data.payload.alphabetize('filename') );
			else
				self.importables.removeAll();
		});		
	}
	
	self.submit = function(form) {
		var param = {'function': 'create'};
		
		$.each(serialize_form(form), function(i,v) {
			param[v.name] = v.value;
		});

		$.getJSON(server_url, param, function(data) {
			if (data.success)
				toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Successfully created new server');
			else
				toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);
		});	
	}
	
	self.import_world = function(form) {
		var param = {'server_name': self.server_name, 'function': 'import_world'};
		$.each(serialize_form(form), function(i,v) {
			param[v.name] = v.value;
		});
		
		if (param.server_name.length && param.archive_file.length) {
			$.getJSON(server_url, param, function(data) {
				if (data.success)
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), 'Created server from archive ' + param.archive_file);
				else
					toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);
			});		
		} else {
				toaster('error', '[{0}] {1}'.format(param.server_name, param.function), 'An unused server name and a supported archive filename required to import');
		}
	}
}

function viewmodel_configs() {
	var self = this;
	self.available_servers = ko.observableArray();
	self.selected_server = ko.observable();
	self.sc = ko.observableArray();
	self.sp = ko.observableArray();
	
	self.populate_servers = function() {
		var param = {server_name: '', 'function': 'list_servers_sane'};
		
		$.getJSON(server_url, param, function(data) {
			if (data.success)
				self.available_servers(data.payload.alphabetize('server_name'));
		});
	}

	self.refresh = function(server_name) {
		var param = {'server_name': server_name, 'function': 'vm_config'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) {
				self.sc.removeAll();
				self.sp.removeAll();
				var a = data.payload.sort(function(a,b) {return (a.section == b.section ? (a.key < b.key ? -1 : 1) : (a.section < b.section ? -1 : 1))});
				$.each(a, function(i,v) {
					if (v.section == 'sectionless')
						self.sp.push(new model_attribute(server_name, v));
					else
						self.sc.push(new model_attribute(server_name, v));
				});
			} else {
				self.sc.removeAll();
				self.sp.removeAll();
			}	
		});		
	}
	
	self.selected_server.subscribe(function (chosen_option) {
		if (chosen_option) {
			self.refresh(chosen_option);
		}
	});

	self.add_sp = function() {
		var new_attr = new model_attribute(self.selected_server, {
			section: 'sectionless',
			key: '',
			value: ''
		}, 'new' );
		self.sp.push(new_attr);
	}

	self.add_sc = function() {
		var new_attr = new model_attribute(self.selected_server, {
			section: '',
			key: '',
			value: ''
		}, 'new');
		self.sc.push(new_attr);	
	}
}

function viewmodel_console() {
	var self = this;
	self.available_servers = ko.observableArray();
	self.selected_server = ko.observable();
	self.loglines = ko.observableArray();
	self.live_feed = ko.observable();
	self.reverse_feed = ko.observable(false);
	self.stream_interval = ko.observable();
	self.command = ko.observable();

	self.populate_servers = function() {
		var param = {server_name: '', 'function': 'list_servers_sane'};
		
		$.getJSON(server_url, param, function(data) {
			if (data.success)
				self.available_servers(data.payload.alphabetize('server_name'));
		});
	}

	self.refresh = function(server_name) {
		var param = {server_name: server_name, 'function': 'list_server_log'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) {
				self.loglines.removeAll();
				var logs = (self.reverse_feed() ? data.payload.reverse() : data.payload);
				$.each(logs, function(i,v) {
					var entry = new model_log_entry(v);
					if (!entry.matches(filter_spam))
						self.loglines.push(entry);
				});
			}
		});		
	}
	
	self.selected_server.subscribe(function (chosen_option) {
		if (chosen_option) 
			self.refresh(chosen_option);
	});	
	
	self.live_feed.subscribe(function() {
		if (self.live_feed() && self.selected_server()) {
			self.stream_interval(setInterval(function() {
				self.refresh(self.selected_server()); 
			}, 3000));
		} else {
			clearInterval(self.stream_interval());
		}		
	});
	
	self.reverse_feed.subscribe(function() {
		self.refresh(self.selected_server());
	});
	
	self.submit_command = function() {
		var param = {server_name: self.selected_server(), 'function': 'console', stuff_text: self.command()};
		
		if (self.command() && self.selected_server()) {
			$.getJSON(server_url, param, function(data) {
				if (data.success)
					toaster('info', '[{0}] {1}'.format(param.server_name, param.function), self.command() );
				else
					toaster('error', '[{0}] {1}'.format(param.server_name, param.function), data.message );
				self.command('');
			});			
		} else {
			toaster('error', '[{0}] {1}'.format(param.server_name, param.function), 'You must select a server and enter a command to continue.');
		}
	}	
	
	self.show_console = function() {
		show_page({dest: '#server_console', nofade: true});
	}
	
	self.show_logparser = function() {
		show_page({dest: '#logparser', nofade: true});
	}
}

function viewmodel_logparser() {
	var self = this;
	self.loglines = ko.observableArray();
	self.available_servers = ko.observableArray();
	self.selected_server = ko.observable();
	self.limit = ko.observable(1000);
	self.include_pattern = ko.observable();;

	self.populate_servers = function() {
		var param = {server_name: '', 'function': 'list_servers_sane'};
		
		$.getJSON(server_url, param, function(data) {
			if (data.success)
				self.available_servers(data.payload.alphabetize('server_name'));
		});
	}
	
	self.refresh = function() {
		var param = {server_name: self.selected_server(), 'function': 'log_tail', limit: self.limit()};
		$.getJSON(server_url, param, function(data) {
			self.loglines.removeAll();
			$.each(data.payload, function(i,v) {
				var entry = new model_log_entry(v);
				if (!entry.matches(filter_spam))
					self.loglines.push(entry);
			});
		});
	}
	
	self.inject = function() {
		var param = {server_name: self.selected_server(), 'function': 'inject_logs'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) {
				toaster(data.success, '[{0}] {1}'.format(param.server_name, param.function), 'server.log successfully inserted into database' );
				self.refresh();
			}
			else
				toaster(data.success, '[{0}] {1}'.format(param.server_name, param.function), data.message );
		});
	}
	
	self.archive = function() {
		var param = {server_name: self.selected_server(), 'function': 'archive_log'};
		$.getJSON(server_url, param, function(data) {
			if (data.success) 
				toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), 'server.log archived and emptied');
			else
				toaster(data.success, '[{0}] {1}'.format(data.server_name, data.function), data.message);		
		});
	}
	
	self.log_match = function() {
		var param = {server_name: self.selected_server(), 'function': 'log_match', pattern: self.include_pattern()};
		$.getJSON(server_url, param, function(data) {
			if (data.success) {	
				self.loglines.removeAll();
				$.each(data.payload, function(i,v) {
					var entry = new model_log_entry(v);
					if (!entry.matches(filter_spam))
						self.loglines.push(entry);
				});
			}
		});		
	}
	
	self.selected_server.subscribe(function (chosen_option) {
		if (chosen_option) 
			self.refresh(chosen_option);
	});	
	
	self.show_console = function() {
		show_page({dest: '#server_console', nofade: true});
	}
	
	self.show_logparser = function() {
		show_page({dest: '#logparser', nofade: true});
	}
}


function viewmodel_health(chart) {
	var self = this;
	
	self.chart = chart;
	self.js_interval = null;
	self.initialized = false;
	
	self.stats = {
		uptime: ko.observable(),
		idletime: ko.observable(),
		root_capacity: ko.observable(),
		used_space: ko.observable(),
		free_space: ko.observable()		
	}
	self.intervals = {
		one: ko.observable(),
		five: ko.observable(),
		fifteen: ko.observable()
	}
	
	self.cpu_data_set = [new TimeSeries(), new TimeSeries(), new TimeSeries()];	
	
	self.tick = function() {
		if (!self.initialized) {
			self.init_chart();
			self.initialized = true;
		}
		
		var param = {server_name: '', 'function': 'vm_health'};

		$.ajax({
			url: server_url,
			dataType: 'json',
			async: false,
			data: param,
			success: function(data) {
				if (data.success) {
					var payload = data.payload[0];
					self.stats.uptime(seconds_to_time(payload.uptime[0]));
					self.stats.idletime(seconds_to_time(payload.uptime[1]));
					
					self.stats.root_capacity(payload.total);
					self.stats.used_space(payload.used);
					self.stats.free_space(payload.free);
					
					self.intervals.one(payload.loadavg[0]);
					self.intervals.five(payload.loadavg[1]);
					self.intervals.fifteen(payload.loadavg[2]);
					
					time = new Date().getTime();
					
					self.cpu_data_set[0].append(time, payload.loadavg[0]);
					self.cpu_data_set[1].append(time, payload.loadavg[1]);
					self.cpu_data_set[2].append(time, payload.loadavg[2]);
				}			
			}
		});
	}

	self.init_chart = function() {
		var seriesOptions = [
			{ strokeStyle: 'rgba(0, 128, 0, 1)', fillStyle: 'rgba(0, 128, 0, 0.1)', lineWidth: 1 },
			{ strokeStyle: 'rgba(255, 255, 0, 1)', fillStyle: 'rgba(255, 255, 0, 0.1)', lineWidth: 1 },
			{ strokeStyle: 'rgba(255, 0, 0, 1)', fillStyle: 'rgba(255, 0, 0, 0.1)', lineWidth: 1 }
		];

		// Build the timeline
		var timeline = new SmoothieChart({ millisPerPixel: 20, grid: { strokeStyle: '#555555', lineWidth: 1, millisPerLine: 1000, verticalSections: 4 }});
		for (var i = 0; i < self.cpu_data_set.length; i++) {
			timeline.addTimeSeries(self.cpu_data_set[i], seriesOptions[i]);
		}
		timeline.streamTo(document.getElementById(self.chart), 3000);		
	}		
}

/* normal page js */

function serialize_form(form) {
	var params = {};

	var form_ = $.map($(form).serializeArray(), function(e,i) {
		if (e.value == '')
			return null;
		else if ( !isNaN(e.value) ) {
			if (parseFloat(e.value).toString() == e.value.toString())
				e.value = parseFloat(e.value);
			else
				e.value = e.value.toString();
		} else if ( e.value.toLowerCase() == 'true' )
			e.value = true;
		else if ( e.value.toLowerCase() == 'false' )
			e.value = false;
		else if ( e.value == 'on' && ['start', 'generate-structures'].indexOf(e.name) >= 0)
			e.value = true;
		else
			e.value = escape(e.value);
		return e;
	});
	return form_;
}

function toaster( type, main_message, additional_content ) {
	switch( type ) {
		case 'success':
		case true:
			toastr.success(additional_content, main_message );    
			break;
		case 'error':
		case false:
			toastr.error(additional_content, main_message );
			break;
		case 'info':
		case null:
			toastr.info(additional_content, main_message );
			break;
		case 'warning':
			toastr.warning(additional_content, main_message );
			break;
	}
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