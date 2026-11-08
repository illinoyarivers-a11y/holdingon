#!/usr/bin/env tclsh
# Web-facing adapter for the original AO3 scraper and epubCreator scripts.
# Usage: tclsh into_epub.tcl WORK_ID OUTPUT_FILE

package require fileutil

set here [file dirname [file normalize [info script]]]
set projectRoot [file normalize [file join $here .. ..]]
set scraper [file join $projectRoot backend scraper ao3.tsh]
set epubCreator [file join $projectRoot backend epub epubCreator.tsh]

if {$argc != 2} {
    puts stderr "Usage: tclsh into_epub.tcl WORK_ID OUTPUT_FILE"
    exit 2
}

set id [lindex $argv 0]
set output [file normalize [lindex $argv 1]]
if {![string is integer -strict $id] || $id <= 0} {
    puts stderr "Invalid AO3 work ID."
    exit 2
}
if {![file exists $scraper]} {
    puts stderr "Missing AO3 scraper: $scraper"
    exit 2
}
if {![file exists $epubCreator]} {
    puts stderr "Missing EPUB creator: $epubCreator"
    exit 2
}

source $scraper

proc TweakHtml {html} {
    # Preserve the original script's cleanup behavior.
    regsub -all {</??a.*?>} $html "" html
    regsub -all {<h3[^>]*>Chapter Text</h3>} $html "" html
    return $html
}

proc ChaptersIntoFiles {ao3 tmpdir} {
    set fnames {}
    set count [$ao3 chapter . count]
    if {$count == 0} { set count 1 }

    for {set idx 1} {$idx <= $count} {incr idx} {
        set html [TweakHtml [$ao3 chapter $idx html]]
        set fname [file join $tmpdir "chapter_${idx}.html"]
        set fout [open $fname w]
        try {
            puts -nonewline $fout $html
        } finally {
            close $fout
        }
        lappend fnames $fname
    }
    return $fnames
}

proc IntoEpub {id output epubCreator} {
    set tmpdir [file join [::fileutil::tempdir] "ao3_epubCreator_[pid]_${id}_[clock microseconds]"]
    file mkdir $tmpdir
    set ao3 ""
    try {
        puts stderr "Fetching AO3 work $id..."
        set ao3 [::AO3::New $id 0 cache]
        set title [$ao3 title]
        set author [$ao3 author]
        puts stderr "Extracting chapters..."
        set files [ChaptersIntoFiles $ao3 $tmpdir]
        $ao3 cleanup
        set ao3 ""

        file mkdir [file dirname $output]
        set cmd [list [info nameofexecutable] $epubCreator \
            -verbose 0 -output $output -title $title -author $author -data]
        lappend cmd {*}$files
        puts stderr "Building EPUB..."
        if {[catch {exec {*}$cmd 2>@1} result options]} {
            return -options $options "EPUB creator failed: $result"
        }
        if {![file exists $output] || [file size $output] == 0} {
            error "EPUB creator finished without producing an output file. $result"
        }
        puts "EPUB_CREATED"
    } finally {
        if {$ao3 ne ""} { catch {$ao3 cleanup} }
        catch {file delete -force $tmpdir}
    }
}

if {[catch {IntoEpub $id $output $epubCreator} message options]} {
    puts stderr $message
    exit 1
}
