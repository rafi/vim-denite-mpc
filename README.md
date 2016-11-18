# denite-mpc

MPD client for Vim to browse your music library by categories and filters.

## Features

- No dependencies (except [denite.nvim])
- Fast socket receiving and buffering
- Asynchronous [denite.nvim] gathering
- Caching for large libraries

## Installation

### Requirements

- Vim or Neovim
- [denite.nvim]
- Python 3.4 or later

Use your favorite plugin manager, mine is [dein.vim].

## Usage

```viml
:Denite mpc:<tag>[:filterby:query:...]
```

Here are a few examples:

- To browse library by dates: `:Denite mpc:date`
- To browse albums, but just for year 2016: `:Denite mpc:album:date:2016`
- To list all Rock (case-sensitive!) artists: `:Denite mpc:artist:genre:Rock`
- To list all track titles from an album: `:Denite mpc:title:album:Blonde\ on\ Blonde`
- You can combine filters: `:Denite mpc:album:artist:Bob\ Dylan:date:1965`

### Configuration

```viml
call denite#custom#var('mpc', 'host', 'localhost')
call denite#custom#var('mpc', 'port', 6600)
call denite#custom#var('mpc', 'timeout', 5.0)
```

- The default values are shown.

## Planned Features

- [x] Custom formatting
- [x] Multiple filters
- [ ] Add / Play / Replace

## Credits & Contribution

Without [Shougo] this wouldn't be possible.
This plugin was developed by Rafael Bodill under the MIT License.

Pull requests are welcome.

[Shougo]: https://github.com/Shougo
[denite.nvim]: https://github.com/Shougo/denite.nvim
[dein.vim]: https://github.com/Shougo/dein.vim
