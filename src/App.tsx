import { useState } from 'react'
import reactLogo from './assets/react.svg'
import './App.css'

function App() {
  return (
    <div className="App">
      <header className="App-header-container">
        <h1 className="App-header">Santa's Labyrinth</h1>
      </header>
      <main>
        <div className="App-placeholder-body">
          <div className="App-image-viewport">
            <img src="images/demo/offer-a-sword-640x480.png"
              style={{ display: "block", width: "320px" }} />
          </div>
          <div className="App-divider">
            <div className="App-scene-title"
              >Offers a Sword</div>
          </div>
          <div className="App-placeholder-dialog">
          <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.
          Pellentesque pellentesque interdum tellus, vitae convallis
          sapien laoreet at. Nam diam libero, tristique ut commodo non.</p>
          <ul className="App-placeholder-dialog-options">
            <li><a href="#">Nam sit amet porta est</a></li>
            <li><a href="#">Suspendisse quis mi sit</a></li>
            <li><a href="#">No</a> </li>
          </ul>
          </div>
          <div className="App-placeholder-prompt">
            <input type="text" style={{boxSizing: "border-box", width: "100%", padding: "14px"}} />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
