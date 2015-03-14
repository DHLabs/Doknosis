window.Diagnosis || = {}

Diagnosis.clear_all = () ->
	# Remove all symptons
	window.symptoms = []
	$( '.rm' ).fadeOut( 'fast', () ->
		$( @parentNode ).remove()
		@
	)

	if $( '#symptoms-list > .help-text' ).length == 0
		$( '#symptoms-list' ).append( '<div class=\'help-text\'>No Symptoms Entered</div>' )
	$( '#results' ).fadeOut();

	@

Diagnosis.get_diagnosis = () ->
	# Don't start another one if it's already running (not sure if it would)
	if $( '#loading-indicator' ).is(":visible")
		window.diagnosis_refresh = true
		return

	if window.symptoms.length == 0
		$( '#results' ).fadeOut();
		# Don't bother with messages.  It's expected that this function will be
		# called when options change regardless of the status of the symptom list.
		# alert 'Please enter some symptoms first!'
		return
	
	$( '#results' ).fadeOut()
	$( '#results-list' ).html( '' )
	$( '#loading-indicator' ).fadeIn()

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
		if window.diagnosis_refresh
			# If another diagnosis was requested (maybe parameters changed) while
			# we were running this one, kick off a new one immediately.
			window.diagnosis_refresh = false
			Diagnosis.get_diagnosis()
	)
	@

$ ->
	# List of symptons to submit
	window.symptoms = []
	window.diagnosis_refresh = false

	# Trigger new diagnosis when parameters change
	window.num_solutions.onchange = () ->
		Diagnosis.get_diagnosis()
	window.num_combinations.onchange = () ->
		Diagnosis.get_diagnosis()
	window.algorithm.onchange = () ->
		Diagnosis.get_diagnosis()
	window.type_identifier.onchange = () ->
		Diagnosis.get_diagnosis()


	# This is triggered when user clicks the close button on one of the symptoms in the symptom window (remove symptom from view and local list, trigger new diagnosis)
	$( document ).on( 'click', '.rm', () ->
		id = $( @ ).data( 'sid' )

		# Find and remove the symptom from js list
		if window.symptoms.indexOf(id) != -1
			window.symptoms.splice(window.symptoms.indexOf(id),1)
			Diagnosis.get_diagnosis()
			
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
			ui.item.value = ''

			$( '#symptoms-list > .help-text' ).remove()
			$( '#symptoms-list' ).append( '<span class="label"><span>' + ui.item.label +
				'</span><span data-sid="' + ui.item.id + '" class="rm">x</span></span>' )
			window.symptoms.push( ui.item.id )
			Diagnosis.get_diagnosis()
	)

	@
