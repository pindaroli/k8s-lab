tell application "Ghostty"
	activate
	set cfg to new surface configuration
	set initial working directory of cfg to "/Users/olindo/prj/k8s-lab/tdarr/node/"
	set win to new window with configuration cfg
	set term to focused terminal of selected tab of win
	input text "./start_node.sh" & return to term
end tell
