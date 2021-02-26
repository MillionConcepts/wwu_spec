# Western Washington University Vis-NIR Spectroscopy Database

The database is in an *early beta* state. Please do not distribute links to
the test server outside of your working group. Bug reports, feature requests,
and instrument filter set submissions are all very welcome. Please send them
directly to mstclair@millionconcepts.com.

## short-term planned features

* add a toggle for simulated illumination in the graph view
* export simulated spectra as distinct CSV files
* improved on-screen display of calculation outputs

## known issues

* calculation foci may sometimes clip out of the graph pane

## patch notes

### v0.31 (2020-12-24)

* fixed a bug related to simultaneous band depth calculations on multiple spectra
* fixed an issue related to focus snapping
* made normalization behaviors clearer and more consistent
* less drawing

### v0.3

* new behavior for 'normalize-to-wavelength' option. Instead of clicking on the
  graph, you may now enter a target wavelength in the box next to the 'wavelength'
  switch in the control panel.
* pan and zoom are now retained when spectra are switched off and on,
  simulation options are changed, or normalization states are changed. 'reset window,'
  as before, will always center the rendered spectra in their current state, 
  should you normalize yourself into a corner of the plane with nothing in it.
* new option to perform calculations on all spectra simultaneously 
* numerous under-the-hood changes to enable futureproofing, extensibility, and bugfixes
* improved pan and zoom behavior from both mouse and window-control widgets
* fixed a bug related to point selection at the right-hand ends of spectra
* fixed issues related to instrumentalized vs. lab spectra selection ambiguities
* visual feedback added for normalization states
* many edge cases and ambiguities in calculation behavior resolved

### v0.24 (12/15/2020)

* optimizations for improved stability, performance, and fault tolerance

### v0.23 (12/11/2020)

* added features for verbose display of object names and citations
* fixed several bugs / unwanted behaviors wrt null or malformed requests
* removed entries of inaccessible databases from search dialogs
* various text changes

### v0.22 (12/10/2020)

* added 'status' page for patch notes, known issues, feature implementation
  roadmap
* feature added to enable arbitrary ordering of filtersets in simulation
  dropdown
* urls / citations added for spectra databases and filtersets
* general cleanup of remote js library and font sources, and partial
  transition to locally-cached versions (reduced page load times, inreased
  stability, etc.)
* fixed bug in graphing / exporting / etc. from ‘select all’ lists
* removed autocomplete feature in search interface
* narrowed navbar (globally) and restored it to graph view
* changed 'roverize' to 'instrumentalize'
* changed default display options to lab lines + instrumentalized points
* created distinct visibility controls for lab lines, lab points, instrument
  lines, instrument points
* changed visual characteristics of graph points and lines
* changed graph line palette
* rounded all calculations and reflectance values to <= 3 values after the
  decimal
* increased axis tick and label font size
* general graph control layout changes + compression
* added features for restricting newly-added spectra to superusers prior to
  review
* fixed a bug related to inappropriately flexible search results from some
  spectra sources

### v0.21 (12/8/2020)

* added custom libraries to sample search and the admin interface
* fixed a bug related to propagation of model choice fields into search
  results
* various small bugfixes and assorted cleanup changes

### v0.2 (2/7/2020)

* Changes from items discussed in 2/3 meeting
* Added handling for uploaded files with multiple reflectance columns
* Changed search to interpret multiple-word queries more loosely
    * For instance, the query 'basalt glass' in the sample name field returns
      all entries containing either 'basalt' OR glass in their sample name
      field
    * UNLESS a sample exists with the exact sample name basalt glass'
* Buggy buttons in results page fixed
* turning on simulated spectrum now continues to display lab spectrum by
  default (can still be toggled off)
* Changed visual design of simulated spectra for improved legibility in this
  mode
* 'Show points' mode active by default
* added tool to normalize all curves to 1 at a given wavelength
    * (workflow: switching it on reveals an 'arm selection' switch, which
      must also be switched on to a normalization wavelength. Without this
      secondary mode, it becomes extremely irritating to try to do
      calculations &c in wavelength normalization mode)
* All calculations are constrained to operate only on a single spectrum
    * User attempts to place calculation anchors on separate spectra are
      ignored
* Simple band depth calculator rewritten. Now two modes:
    * Automatically finds local minimum
    * Calculates band depth at point selected by user
* filter sets added: Pathfinder IMP, MER Pancam, Mastcam-Z, Landsat OLI
* Added functionality for dynamically switching filter sets for simulations
* All filtersets now also save simulated spectra with no illumination (i.e.,
  illumination = 1, reflectance = radiance at all points)
* 'Locator line’ changed to 'vertical line'
* Redesign of entire site in WWU identity colors
    * the only elements drawn with colors outside of the identity color
      palette are simulated spectra
* Redesigned about page

### v0.1 (1/31/2020)

* First release of major application redesign.
* updated to python 3.x / django 3.x. Backend changes related to update not
  specified here in detail.
* Extensively refactored Python and JS code for maintainability and
  extensibility. Individual changes too numerous to list.
* Broad visual redesign.
* replaced postgreSQL with SQLite (more maintainable, portable, and
  performant for small database size with few concurrent users)
* Altered all existing database models; changes included fields
  inappropriately referring to 'mineral' properties to 'sample' or 'material'
  as appropriate
* improved behavior of autocomplete dialogs
* mass sample type flagging actions replaced with broader mass editing
  functionality
* added image upload and processing functionality
* added associated image download and display functionality
* improved upload input processing and UX
* added capability to insert filter sets and illumination conditions into
  database
* added tools for simulating spectra viewed through filter sets under
  specified illumination conditions
* added 'reset zoom' button in graph view
* added 'shrink' button in graph view for more working space
* improved scrolling and zoom behavior in graph view
* Fixed various bugs related to widget positioning in graph view
* Redesigned control interface and layout of graph view for improved
  usability and accessibility
* fixed a bug related to graph boundary setting when graphing multiple
  spectra
* added calculators for simple band depth, ratio, and slope in graph view
* added option to drop multiple vertical lines in graph view
* added option to linearly peak-normalize spectra to 1 in graph view
* added option to y-offset spectra in graph view
* added user-facing bulk-upload capability
* advanced search replaced with 'any' field
* results view redesigned to reduce amount of data presented to users for
  improved readability and navigation
