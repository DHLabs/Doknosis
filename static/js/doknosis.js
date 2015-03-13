// Generated by CoffeeScript 1.9.1
(function() {
  window.Diagnosis || (window.Diagnosis = {});

  Diagnosis.clear_all = function() {
    window.symptoms = [];
    $('.rm').fadeOut('fast', function() {
      $(this.parentNode).remove();
      return this;
    });
    if ($('#symptoms-list > .help-text').length === 0) {
      $('#symptoms-list').append('<div class=\'help-text\'>No Symptoms Entered</div>');
    }
    $('#results').hide();
    return this;
  };

  Diagnosis.get_diagnosis = function() {
    var params;
    if (window.symptoms.length === 0) {
      alert('Please enter some symptoms first!');
      return;
    }
    $('#results').hide();
    $('#results-list').html('');
    $('#loading-indicator').show();
    if ($('#banner-bar').data('at_top') !== true) {
      $('#banner-bar').data('at_top', true).animate({
        top: '0%',
        marginTop: '+=109'
      }, 500, null);
    }
    params = {
      findings: window.symptoms.join(','),
      num_solutions: $('#num_solutions').val(),
      num_combinations: $('#num_combinations').val(),
      type_identifier: $('#type_identifier').val(),
      algorithm: $('#algorithm').val()
    };
    $.getJSON('/diagnosis_result', params, function(data) {
      var dat, i, len, ref, results_table;
      if (data.success === !true) {
        alert('Failure -- ' + data.error);
        $('#loading-indicator').hide();
        return;
      }
      $('#query-time').html("DB QUERY TIME: " + data.query_time);
      $('<div/>').addClass('diagnosis').html("<strong>Most Likely:</strong> " + data.greedy).appendTo('#results-list');
      results_table = $('<table/>').addClass('results-table').addClass('table').addClass('table-striped').append('<tr><th>Name</th><th>Score</th></tr>');
      ref = data.other;
      for (i = 0, len = ref.length; i < len; i++) {
        dat = ref[i];
        $('<tr/>').append("<td> " + dat[0] + " </td>").append("<td> " + dat[1] + " </td>").appendTo(results_table);
      }
      $('#loading-indicator').hide();
      results_table.appendTo('#results-list');
      return $('#results').fadeIn();
    });
    return this;
  };

  $(function() {
    window.symptoms = [];
    $(document).on('click', '.rm', function() {
      var id;
      id = $(this).data('sid');
      if (window.symptoms.indexOf(id) !== -1) {
        window.symptoms.splice(window.symptoms.indexOf(id), 1);
      }
      return $(this.parentNode).fadeOut('fast', function() {
        $(this).remove();
        if ($('#symptoms-list > .label').length === 0) {
          return $('#symptoms-list').append('<div class=\'help-text\'>No Symptoms Entered</div>');
        }
      });
    });
    $("#symptoms").autocomplete({
      source: '/api/finding/autocomplete',
      select: function(event, ui) {
        var text;
        text = ui.item.label;
        ui.item.value = '';
        $('#symptoms-list > .help-text').remove();
        $('#symptoms-list').append('<span class="label"><span>' + text + '</span><span data-sid="' + ui.item.id + '" class="rm">x</span></span>');
        return window.symptoms.push(ui.item.id);
      }
    });
    return this;
  });

}).call(this);
