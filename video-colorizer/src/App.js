import logo from './logo.svg';
import './App.css';
import Button from 'react-bootstrap/Button';

import React from 'react';
class Main extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      imageURL: '',
    };

    this.handleUploadImage = this.handleUploadImage.bind(this);
  }

  handleUploadImage(ev) {
    ev.preventDefault();

    const data = new FormData();
    data.append('file', this.uploadInput.files[0]);
    data.append('filename', "abc");

    fetch('http://localhost:4000/upload', {
      method: 'POST',
      body: data,
    }).then((response) => {
      response.json().then((body) => {
        this.setState({ imageURL: `http://localhost:4000/${body.file}` });
      });
    });
  }

  render() {
    return (
      <div>
        <header>
        <h1 class="header-1">Image & Video</h1>
        <h1 class="header-2">Colorizer</h1>
        </header>
      <div class='center'>
        <form onSubmit={this.handleUploadImage}>
        <div>
          <input ref={(ref) => { this.uploadInput = ref; }} type="file" />
        </div>
        {/* <div>
          <input ref={(ref) => { this.fileName = ref; }} type="text" placeholder="Enter the desired name of file" />
        </div> */}
        <br />
        <div>
          <button className='button-77' size="lg">Upload</button>
        </div>
        <div class = "parent">
          <div class = "child"><h5>Image Line Art ? </h5></div>
        <div class = "child"><input type="checkbox" className = "toggle-body" id="switch" /><label className = "toggle-label" for="switch">Toggle</label>
        </div>
        </div>
      </form>
      </div>
      </div>
    );
  }
}

export default Main;