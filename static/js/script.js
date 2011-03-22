var LS_WEBS = 'webs';

var quotes = [
{'text': 'A real job is a job you hate.'},
{'text': 'From now on, I\'ll connect the dots my own way.'},
{'text': 'Genius is never understood in its own time.'},
{'text': 'Getting an inch of snow is like winning 10 cents in the lottery.'},
{'text': 'God put me on this earth to accomplish a certain number of things. Right now I am so far behind that I will never die.'},
{'text': 'Heck, what\'s a little extortion among friends?'},
{'text': 'I find my life is a lot easier the lower I keep everyone\'s expectations.'},
{'text': 'I know the world isn\'t fair, but why isn\'t it ever unfair in my favor?'},
{'text': 'I liked things better when I didn\'t understand them.'}
];

function searchBooks() {
  $('#search_results').html('Searching for matching books...');
  $.ajax({
     url: 'service/booksearch?keywords=' + $('#keywords').val(),
     dataType: 'json',
     type: 'get', 
     success: function(books) {
       $('#search_results').html('')
       for (var i = 0; i < books.length; i++) {
         addResult(books[i]);
       }
     },
     error: function(xhr, status) {
     }
    });  
}

function addResult(book) {
  var div = $('<div class="result"></div>');
  if (book.images.small) {
    div.append('<div class="result_thumb"><img src="' + book.images.small + '"></div>');
  }
  div.append('<span class="result_title">' + book.title + '</span><br><span class="result_author">' + book.author + '</span>');
  div.click(function() {
    var url = 'http://' + window.location.host + '/' + book.asin;
    window.open(url, '_blank');
  });
  $('#search_results').append(div);
}

function showQuote() {
  var randNum = Math.floor(Math.random()*quotes.length)
  $('#web_wait_quote').html('<div class="quote_text">"' + quotes[randNum].text + '"</div><div class="quote_author">Bill Watterson</div>');
}

function getWeb(asin) {
  var winHeight = $(window).height()-20;
  $('#web_wrapper').height(winHeight).width(winHeight+250);
  $('#web_graph').height(winHeight-20).width(winHeight+200);
  $('#web_sidebar').hide();
  $.ajax({
    url: 'service/bookweb?asin=' + asin,
    dataType: 'json',
    type: 'get', 
    success: function(info) {
      if (info.status && info.status == 'deferred') {
        $('#web_wait_msg').html('Searching for similar books...This can take a few minutes, thanks for your patience!<br><br>');
        $('#web_wait_msg').append('Enjoy some of my favorite literary quotes while you wait:');
        var quoteTimer = window.setInterval(showQuote, 5000);
        showQuote();
        window.setTimeout(function() { getWeb(asin) }, 1000*5); 
      } else {
        $('#web_graph').html('');
        $('#web_graph').height(winHeight-20).width(winHeight);
        $('#web_sidebar').height(winHeight-10).width(200);
        $('#web_sidebar').show();
        if (quoteTimer) window.clearInterval(quoteTimer);
        showWeb(info);
      }
    },
    error: function(xhr, status) {
      console.log(status);
    }
   });  
}

function showWeb(info) {
  info.seen_asins = [];
  var json = getNodeInfo(info, info.asin);
  
  var infovis = document.getElementById('web_graph');
  var w = infovis.offsetWidth - 50, h = infovis.offsetHeight - 75;
  
  //init Hypertree
  var ht = new $jit.Hypertree({
    //id of the visualization container
    injectInto: 'web_graph',
    //canvas width and height
    width: w,
    height: h,
    //Change node and edge styles such as
    //color, width and dimensions.
    Node: {
        dim: 9,
        color: "#000"
    },
    Edge: {
        lineWidth: 2,
        color: "#889770"
    },
    //Attach event handlers and add text to the
    //labels. This method is only triggered on label
    //creation
    onCreateLabel: function(domElement, node){
        domElement.innerHTML = '<img class="web_thumb" src="' + node.data.images.small + '">';
        $jit.util.addEvent(domElement, 'mouseover', function () {
            domElement.style.zIndex = 3000;
        });
        $jit.util.addEvent(domElement, 'mouseout', function () {
            domElement.style.zIndex = 'auto';
        });
        $jit.util.addEvent(domElement, 'mouseover', function () {
          $('#web_details').html('');
          $('#web_details').append('<img src="' + node.data.images.medium + '">');
          $('#web_details').append('<h3>' + node.data.title + '</h3>');
          $('#web_details').append('By ' + node.data.author);
          $('#web_details').append('<Br>' + node.data.price);
        });
        $jit.util.addEvent(domElement, 'click', function () {
          var url = 'http://www.amazon.com/gp/product/' + node.data.asin + '?tag=amazonsimilar-20';
          window.open(url, '_blank');
        });
    },
    //Change node styles when labels are placed
    //or moved.
    onPlaceLabel: function(domElement, node){
        var style = domElement.style;
        var width, height;
        if (node._depth == 0) {
          width = 75;
          height = 75;
        } else if(node._depth == 1){
          width = 55;
          height = 55; 
        } else if(node._depth == 2){
          width = 40;
          height = 40;
        }
        
        style.width = width + 'px';
        style.height = height + 'px';
        
        var left = parseInt(style.left);
        var top = parseInt(style.top);
        style.left = Math.floor(left - width/2) + 'px';
        style.top = Math.floor(top - height/2) + 'px';
    },
    
    onAfterCompute: function(){
    }
  });
  //load JSON data.
  ht.loadJSON(json);
  //compute positions and plot.
  ht.refresh();
  //end
  ht.controller.onAfterCompute();
}

function getNodeInfo(info, asin) {
  var node = getNodeData(info, asin);
  // This is admittedly not the smart way to do this. Oh well.
  
  // First level
  var children = info.book_graph[asin];
  for (var i = 0; i < children.length; i++) {
    if (!info.seen_asins[children[i]]) {
      node.children.push(getNodeData(info, children[i]));
      
    }
  }
  // Second level
  for (var i = 0; i < node.children.length; i++) {
    var grandchildren = info.book_graph[(node.children[i].data.asin)];
    if (grandchildren) {
      for (var j = 0; j < grandchildren.length; j++) {
        if (!info.seen_asins[grandchildren[j]]) {
          node.children[i].children.push(getNodeData(info, grandchildren[j]));
        }
      }
    }
  }
  return node;
}

function getNodeData(info, asin) {
  var node = {};
  node.id = asin + '-' + Math.floor(Math.random()*999);
  node.data = info.book_details[asin];
  node.name = node.data.title;
  node.children = [];
  info.seen_asins[asin] = true;
  return node;
}

function getWebs(order, div, num) {
  $.ajax({
    url: 'service/bookwebs?order=' + order + '&num=' + num,
    dataType: 'json',
    type: 'get', 
    success: function(rounds) {
      for (var i = 0; i < rounds.length; i++) {
        addWeb(rounds[i], div);
      }
    },
    error: function(xhr, status) {
    }
   });
}


function addWeb(web, parent) {
  var url = 'http://' + window.location.host + '/' + web.asin;
  var div = $('<div class="round"></div>');
  div.html('<a href="' + url + '">' + web.title + '</a>');
  div.click(function() {
    window.location.href = url;
  })
  parent.append(div);
}

function getYours(num) {
  if (!supportsStorage) return;
  
  function dateSort(a, b){
    //Compare "a" and "b" in some fashion, and return -1, 0, or 1
    return (b.date - a.date);
  }
  
  var rounds = localStorage.getItem(LS_WEBS);
  if (rounds) {
    rounds = JSON.parse(rounds);
    rounds.sort(dateSort);
    $('#yours').empty();
    for (var i = 0; i < Math.min(num, rounds.length); i++) {
      addWeb(rounds[i], $('#yours'));
    }
    $('#yours_section').show();
  }
}


function supportsStorage() {
  try {
    return 'localStorage' in window && window['localStorage'] !== null;
  } catch (e) {
    return false;
  }
}


function shareBuzz() {
  var message = 'Check out the translation I got from Translation Telephone!';
  var url = 'http://www.google.com/buzz/post?' +
    'message=' + message.replace(' ', '%20')  + 
    '&url=' + encodeURIComponent(window.location.href);
  window.open(url,
    '_blank', 'resizable=0,scrollbars=0,width=690,height=415');
}

function shareTwitter() {
  var tweetUrl = 'http://www.translation-telephone.com/#4249';
  var url = 'http://www.twitter.com/share' +
    '?url=' + tweetUrl.replace('#', '%23');
    //'&text=Check+out+this+funny+translation';
  //replace('#', '%23');
  window.open(url,
    '_blank', 'resizable=0,scrollbars=0,width=690,height=415');
}

function shareFacebook() {
  var url = 'http://www.facebook.com/sharer.php?' +
    't=Check+out+this+funny+translation';
  window.open(url,
    '_blank', 'resizable=0,scrollbars=0,width=690,height=415');
}


function initMain() {
   getWebs('-date', $('#recent'), 3);
   getWebs('-views', $('#popular'), 3);
   getYours(3);
}

function initRecent() {
  getWebs('-date', $('#recent'), 30);
}

function initPopular() {
  getWebs('-views', $('#popular'), 30);
}

function initYours() {
  getYours(1000);
}

function initWeb() {
  var asin = window.location.pathname.substr(1)
  getWeb(asin);
}

