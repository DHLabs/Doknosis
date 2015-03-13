clear_all = () ->
	# Remove all symptons
	window.symptoms = []
	$( '.rm' ).fadeOut( 'fast', () ->
		$( @parentNode ).remove()
		@
	)

	if $( '#symptoms-list > .help-text' ).length == 0
		$( '#symptoms-list' ).append( '<div class=\'help-text\'>No Symptoms Entered</div>' )
	$( '#results' ).hide();

	@

get_diagnosis = () ->
	if window.symptoms.length == 0
		alert 'Please enter some symptoms first!'
		return
	
	$( '#results' ).hide()
	$( '#results-list' ).html( '' )
	$( '#loading-indicator' ).show()

	if $( '#banner-bar' ).data( 'at_top' ) != true
		$( '#banner-bar' ).data( 'at_top', true ).animate(
			{ top: '0%', marginTop: '+=109'},
			500,
			null
		)

	params =
		findings: 			window.symptoms.join( ',' )
		num_solutions:  	$( '#num_solutions' ).val()
		num_combinations:	$( '#num_combinations' ).val()
		type_identifier:	$( '#type_identifier' ).val()
		algorithm:			$( '#algorithm' ).val()

	$.getJSON( '/diagnosis_result', params, ( data ) ->

		if data.success is not true
			alert 'Failure -- '+data.error
			$( '#loading-indicator' ).hide()
			return

		$( '#query-time' ).html( "DB QUERY TIME: #{data.query_time}" )

		# Setup the most likely result text
		$( '<div/>' ).addClass( 'diagnosis' )
					 .html( "<strong>Most Likely:</strong> #{data.greedy}" )
					 .appendTo( '#results-list' )

		# Create results table
		results_table = $( '<table/>' ).addClass( 'results-table' )
									   .addClass( 'table' )
									   .addClass( 'table-striped' )
									   .append( '<tr><th>Name</th><th>Score</th></tr>' )

		for dat in data.other
			$( '<tr/>' ).append( "<td> #{dat[0]} </td>" )
						.append( "<td> #{dat[1]} </td>" )
						.appendTo( results_table )

		# Hide loading indicator and display results table
		$( '#loading-indicator' ).hide()
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

		# Find and remove the symptom from js list
		if window.symptoms.indexOf(id) != -1
			window.symptoms.splice(window.symptoms.indexOf(id),1)

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
