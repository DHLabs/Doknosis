toggle_loading = () ->
	$( '#loading-indicator' ).toggle();
	@

clear_all = () ->
	# Remove all symptons
	window.symptoms = []
	$( '.rm' ).fadeOut( 'fast', () ->
		$( @parentNode ).remove()
		@
	)

	$( '#symptoms-list' ).append( '<div class=\'help-text\'>No Symptoms Entered</div>' )
	$( '#results' ).hide();

	@

get_diagnosis = () ->

	if window.symptoms.length == 0
		alert 'Please enter some symptoms first!'
		return

	$( '#results' ).hide()
	$( '#results-list' ).html( '' )

	if $( '#banner-bar' ).data( 'at_top' ) != true
		$( '#banner-bar' ).data( 'at_top', true ).animate(
			{ top: '0%', marginTop: '+=109'},
			500,
			toggle_loading
		)

	params =
		findings: 			window.symptoms.join( ',' )
		num_solutions:  	$( '#num_solutions' ).val()
		num_combinations:	$( '#num_combinations' ).val()
		algorithm:			$( '#algorithm' ).val()

	$.getJSON( '/diagnosis_result', params, ( data ) ->

		if data.success is not true
			return

		$( '#query-time' ).html( "DB QUERY TIME: #{data.query_time}" )

		# Setup the most likely result text
		$( '<div/>' ).css( 'margin', '16px 0' )
					 .html( "<strong>Most Likely:</strong> #{data.greedy}" )
					 .appendTo( '#results-list' )

		# Create results table
		results_table = $( '<table/>' ).addClass( 'table' )
									   .addClass( 'table-striped' )
									   .append( '<tr><th>Name</th><th>Score</th></tr>' )

		for i in [0..data.other.length-1]
			$( '<tr/>' ).append( "<td> #{data.other[i][0]} </td>" )
						.append( "<td> #{data.other[i][1]} </td>" )
						.appendTo( results_table )

		# Hide loading indicator and display results table
		toggle_loading()
		results_table.appendTo( '#results-list' )
		$( '#results' ).fadeIn()
	)
	@

$ ->
	# List of symptons to submit
	window.symptoms = []

	# Remove symptom from list
	$( document ).on( 'click', '.rm', () ->
		id = $( @ ).data( 'sid' )

		# Loop through and attempt to find matching id
		for i in [0..window.symptoms.length-1]

			if window.symptoms[ i ] == id
				# Remove from array
				window.symptoms.splice( i, 1 )

		# Remove the label from the symptoms box
		$( @parentNode ).fadeOut( 'fast', () ->

			$( @ ).remove()

			# If this is the last label in the symptons box, add the
			# "No Symptoms Entered" help-text into the box.
			if $( '#symptoms-list > .label' ).length == 0
				$( '#symptoms-list' ).append( '<div class=\'help-text\'>No Symptoms Entered</div>' )
		)
	)

	$( "#symptoms" ).autocomplete(
		source: '/api/finding/autocomplete',
		select: ( event, ui ) ->
			text = ui.item.label
			ui.item.value = ''

			$( '#symptoms-list > .help-text' ).remove()
			$( '#symptoms-list' ).append( '<span class="label"><span>' + text +
				'</span><span data-sid="' + ui.item.id + '" class="rm">x</span></span>' )

			window.symptoms.push( ui.item.id )
	)

	@