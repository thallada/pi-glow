if tmux has-session -t lights &> /dev/null
then
	tmux send-keys -t lights C-c; tmux kill-session -t lights;
else
	tmux new-session -s lights -d; sleep 1; tmux send-keys -t lights python SPACE pi-glow/glow.py SPACE -n ENTER;
fi
