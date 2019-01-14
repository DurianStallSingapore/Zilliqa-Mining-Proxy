String.prototype.format = function() {
    let formatted = this;
    for( var arg in arguments ) {
        formatted = formatted.replace("{" + arg + "}", arguments[arg]);
    }
    return formatted;
};

function valid_hex_str(s, size) {
  s = $.trim(s).toLowerCase().replace(/"/gi, '').replace(/'/gi, '');
  if (!s.startsWith("0x")) {
    s = "0x" + s;
  }
  if (s.length !== size) {
    return false;
  }
  return s;
}

function valid_email(value) {
  return /\S+@\S+\.\S+/.test(value);
}

function jsonrpc(url, method, params, on_success, on_error) {
  $.ajax({
    url: url,
    type: "POST",
    dataType: "json",
    data: JSON.stringify({
      id: 42, jsonrpc: '2.0',
      method: method,
      params: params
    }),
    success: function (resp) {
      console.log(resp);

      if (resp.error) {
        let error = resp.error;
        on_error('{0}: {1}'.format(error.message, error.data));
        return;
      }
      on_success(resp.result);
    },
    error: function (err) {
      console.log(err);
      let error = err.responseJSON.error;
      on_error('{0}: {1}'.format(error.message, error.data));
    }
  });
}

$.fn.removeClassPrefix = function (prefix) {
    this.each( function ( i, it ) {
        let classes = it.className.split(" ").map(function (item) {
            return item.indexOf(prefix) === 0 ? "" : item;
        });
        classes = classes.filter(function (name) {
          return name.length > 0;
        });
        it.className = classes.join(" ");
    });

    return this;
};

function error_msg(elem, msg, style) {
  let $elem = $(elem);
  $elem.text(msg).removeClassPrefix("alert-");

  if (style) {
    $elem.show().addClass("alert-" + style);
  } else {
    $elem.hide();
  }
}

function append_msg(elem, msg, style) {
  let $elem = $(elem);
  let $new_elem = $elem.clone().attr("id", "");

  $new_elem.text(msg).removeClassPrefix("alert-");
  $new_elem.show().addClass("alert-" + style);

  $elem.after($new_elem);
}
