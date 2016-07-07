(function ($) {
	/**
	 * The illustrationBrowser jQuery plugin provides the GUI functionality
	 * for the illustration viewer.
	 */
	var methods = {
		init: function(options) {
			return this.each(function() {
				var component = $(this);
				component.data('options', options);
				component.data('cache', {});
		    	component.find('a').on('click', function() {
		    		var link = $(this);
		    		var book_id = link.data('id');
		    		var cache =  component.data('cache');
		    		if(!cache[book_id]) {
		    			cache[book_id] = link.data('illustrations').map(function (illustration) {return {id: illustration}});
		    		}
		    		component.data('current_book_id', book_id);
		    		component.data('current_illustration_idx', 0);
		    		component.data('book').find('span.title').html(link.html()).attr('title', link.html());
		    		component.illustrationBrowser('show');
		    		return false;
		    	});
		    	var win = $(window);
		    	var image_size = 320;
		    	component.data('flickr-sizes', ['Small 320', 'Small']);
		    	if(win.height() > 700 && win.width() > 750) {
		    		image_size = 640;
			    	component.data('flickr-sizes', ['Medium 640', 'Medium', 'Small 320', 'Small']);
		    	} 
	    		component.data('image-size', image_size);
		    	var book = $('<div class="book-overlay size-' + image_size + '" style="display:none;">' +
		    			'<a href="#" class="prev">&lang;</a>' +
		    			'<a href="#" class="next">&rang;</a>' +
		    			'<span class="title" title="Book Title">Book Title</span>' +
		    			'<span class="pagenr">Illustration 1 of 1</span>' +
		    			'<ul class="pages" title="Click on the image to see the full details on Flickr">' +
		    			'</ul>' +
		    			'</div>');
		    	component.data('book', book);
		    	book.find('a.prev').on('click', function() {
		    		component.illustrationBrowser('prev');
		    		return false;
		    	});
		    	book.find('a.next').on('click', function() {
		    		component.illustrationBrowser('next');
		    		return false;
		    	});
		    	var overlay = $('<div class="ui-widget-overlay" style="display:none;"></div>');
		    	overlay.on('click', function() {
		    		component.illustrationBrowser('hide');
		    	});
		    	component.data('overlay', overlay);
		    	$(document.body).append(book).append(overlay);
			});
		},
		show: function() {
			return this.each(function() {
				var component = $(this);
				var cache = component.data('cache');
				var book = component.data('book');
				component.data('overlay').show();
				book.show();
				book.find('ul.pages').scrollLeft(0);
				book.position({
					my: 'center center',
					at: 'center center',
					of: $(window)
				});
				book.children('a.prev').position({
					my: 'right+2px center',
					at: 'left center',
					of: book
				});
				book.children('a.next').position({
					my: 'left-2px center',
					at: 'right center',
					of: book
				});
				book.children('span.pagenr').position({
					my: 'right top-2px',
					at: 'right bottom',
					of: book
				});
				book.children('span.title').position({
					my: 'left bottom+2px',
					at: 'left top',
					of: book
				});
				var pages = book.children('ul.pages');
				pages.empty();
				var illustrations = cache[component.data('current_book_id')];
				for(var idx in illustrations) {
					var item = $('<li><a href="http://www.flickr.com/photos/britishlibrary/' + illustrations[idx].id + '" target="_blank"><img src="' + component.data('options').spinner + '"/></a></li>');
					pages.append(item);
				}
				$(window).on('keyup.illustrationBrowser', function(ev) {
					if(ev.keyCode == 37) {
						component.illustrationBrowser('prev');
					} else if(ev.keyCode == 39) {
						component.illustrationBrowser('next');
					} else if(ev.keyCode == 27) {
						component.illustrationBrowser('hide');
					}
				});
			}).illustrationBrowser('load').illustrationBrowser('repaint');
		},
		hide: function() {
			return this.each(function() {
				var component = $(this);
				component.data('book').hide();
				component.data('overlay').hide();
				$(window).off('keyup.illustrationBrowser');
			});
		},
		prev: function() {
			return this.each(function() {
				var component = $(this);
				component.data('current_illustration_idx', Math.max(0, component.data('current_illustration_idx') - 1));
			}).illustrationBrowser('load').illustrationBrowser('repaint');
		},
		next: function() {
			return this.each(function() {
				var component = $(this);
				component.data('current_illustration_idx', Math.min(component.data('cache')[component.data('current_book_id')].length - 1, component.data('current_illustration_idx') + 1));
			}).illustrationBrowser('load').illustrationBrowser('repaint');
		},
		load: function() {
			return this.each(function() {
				var component = $(this);
				var options = component.data('options');
				var illustration = component.data('cache')[component.data('current_book_id')][component.data('current_illustration_idx')];
				if(illustration) {
					if(illustration.source) {
						component.data('book').find('ul.pages li:nth-child(' + (component.data('current_illustration_idx') + 1) + ') img').attr('src', illustration.source);
					} else {
						$.ajax(options.flickr.url, {
							data: {
								method: 'flickr.photos.getSizes',
								api_key: options.flickr.key,
								format: 'json',
								nojsoncallback: '1',
								photo_id: illustration.id
							}
						}).done(function(data) {
							var size_preference = component.data('flickr-sizes');
							var found = false;
							for(var idx in size_preference) {
								for(var idx2 in data.sizes.size) {
									if(data.sizes.size[idx2].label == size_preference[idx]) {
										component.data('book').find('ul.pages li:nth-child(' + (component.data('current_illustration_idx') + 1) + ') img').attr('src', data.sizes.size[idx2].source);
										illustration.source = data.sizes.size[idx2].source;
										found = true;
										break;
									}
								}
								if(found) {
									break;
								}
							}
						});
					}
				}
			});
		},
		repaint: function() {
			return this.each(function() {
				var component = $(this);
				var book = component.data('book');
				var current_illustration_idx = component.data('current_illustration_idx');
				var illustration_count = component.data('cache')[component.data('current_book_id')].length;
				book.find('ul.pages').animate({scrollLeft: component.data('current_illustration_idx') * (component.data('image-size') + 20)});
				if(current_illustration_idx == illustration_count - 1) {
					book.find('a.next').addClass('disabled');
				} else {
					book.find('a.next').removeClass('disabled');
				}
				if(current_illustration_idx == 0) {
					book.find('a.prev').addClass('disabled');
				} else {
					book.find('a.prev').removeClass('disabled');
				}
				book.find('span.pagenr').html('Illustration ' + (current_illustration_idx + 1) + ' of ' + illustration_count);
			});
		}
	};
		
	$.fn.illustrationBrowser = function(method) {
	    if(methods[method]) {
	   		return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
	    } else if(typeof method === 'object' || !method) {
	   		return methods.init.apply(this, arguments);
	   	} else {
	   		$.error('Method ' +  method + ' does not exist on jQuery.illustrationBrowser');
	   	}
	};
}(jQuery));

(function ($) {
	/**
	 * The textScroller scrolls the shelf keywords.
	 */
	var methods = {
		init: function(options) {
			return this.each(function() {
				var item = $(this);
				item.on('mouseover', function() {
					item.textScroller('start');
				});
				item.on('mouseout', function() {
					item.textScroller('stop');
				});
			});
		},
		start: function() {
			return this.each(function() {
				var item = $(this);
				item.find('.keywords-scroll').css('display', 'block');
				var width = item.find('.keywords-scroll').outerWidth(true) - item.find('.keywords').width();
				item.find('.keywords-scroll').animate({
					left: -width
				}, {
					duration: width * 30,
					easing: 'linear',
					done: function() {
						item.data('scroll.timeout', setTimeout(function() {
							item.find('.keywords-scroll').animate({
								left: 0
							}, {
								duration: width * 30,
								easing: 'linear'
							});
						}, 2000));
					}
				});
			});
		},
		stop: function() {
			return this.each(function() {
				var item = $(this);
				item.find('.keywords-scroll').stop().css('left', '0px').hide();
				clearTimeout(item.data('scroll.timeout'));
			});
		}
	};
		
	$.fn.textScroller = function(method) {
	    if(methods[method]) {
	   		return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
	    } else if(typeof method === 'object' || !method) {
	   		return methods.init.apply(this, arguments);
	   	} else {
	   		$.error('Method ' +  method + ' does not exist on jQuery.textScroller');
	   	}
	};
}(jQuery));
