import logo from './logo.svg';
import './App.css';
import Button from 'react-bootstrap/Button';

import React from 'react';
class Main extends React.Component {
  constructor(props) {
    super(props);
    
    this.state = {
      buttonName:"Upload"
    };
    this.boxChecked = React.createRef();
    this.handleUploadImage = this.handleUploadImage.bind(this);
  }
  
  
  handleUploadImage(ev) {
    ev.preventDefault();
    
    const data = new FormData();
    data.append('file', this.uploadInput.files[0]);
    data.append('filename', "abc");
    var variable = "upload1";
    console.log(this.boxChecked.current.checked);
    if(this.boxChecked.current.checked)
    {
      variable = "upload2";
    }
    else{
      variable = "upload1";
    }
    fetch('http://localhost:4000/'+variable, {
    method: 'POST',
    body: data,
  }).then((response) => {
    console.log("Hello world inside then block")
    response.json().then((body) => {
      console.log(body)
      this.setState({buttonName:'Downloaded'})
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
  <br />
  <div>
  <button className='button-77' size="lg">{this.state.buttonName}</button>
  </div>
  <div class = "parent">
  <div class = "child"><h5>Video Line Art ? </h5></div>
  <div class = "child"><input ref={this.boxChecked} type="checkbox" value="True" className = "toggle-body" id="switch" /><label className = "toggle-label" for="switch">Toggle</label>
  </div>
  </div>
  </form>
  </div>
  </div>
  );
}
}
export default Main;